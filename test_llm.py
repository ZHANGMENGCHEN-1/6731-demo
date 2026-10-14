"""离线验证请求/响应流程，不使用真实 Key 或网络。"""
import json
import unittest
from unittest.mock import MagicMock, patch
import requests
import agent

SETTINGS = {"provider": "zhipu", "model": "glm-5.3", "api_key": "offline-test"}


def event(data):
    return "data: " + json.dumps(data, ensure_ascii=False)


class LLMTests(unittest.TestCase):
    def request(self, lines, status=200):
        response = MagicMock()
        response.status_code = status
        response.iter_lines.return_value = iter(lines)
        response.__enter__.return_value = response
        return response

    @patch.object(agent, "llm_settings", return_value=SETTINGS)
    @patch.object(agent.requests, "post")
    def test_stream_and_history(self, post, settings):
        post.return_value = self.request([
            event({"choices": [{"delta": {"reasoning_content": "不展示的推理"}}]}),
            event({"choices": [{"delta": {"content": "真实"}}]}),
            event({"choices": [{"delta": {"content": "解读"}, "finish_reason": "stop"}]}),
            "data: [DONE]",
        ])
        history = [{"role": "user", "content": "之前的问题"}, {"role": "assistant", "content": "之前的回复"}]
        updates = []
        result = agent.run_agent("B01228 的持仓趋势怎么样？", history, on_text=updates.append)
        self.assertEqual(updates, ["真实", "真实解读"])
        self.assertEqual(result["response"], "真实解读")
        self.assertIsNone(result["llm_error"])
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["messages"][1:3], history)
        self.assertIn("21868100", body["messages"][-1]["content"])
        self.assertEqual(body["model"], "glm-5.3")
        self.assertEqual(body["reasoning_effort"], "low")
        self.assertTrue(body["stream"])

    @patch.object(agent, "llm_settings", return_value=SETTINGS)
    @patch.object(agent.requests, "post")
    def test_updates_before_stream_completes(self, post, settings):
        updates = []

        def lines():
            yield event({"choices": [{"delta": {"content": "第一段"}}]})
            self.assertEqual(updates, ["第一段"])
            yield event({"choices": [{"delta": {"content": "第二段"}}]})
            self.assertEqual(updates, ["第一段", "第一段第二段"])
            yield "data: [DONE]"

        post.return_value = self.request(lines())
        self.assertEqual(agent.call_llm([], on_text=updates.append), "第一段第二段")

    @patch.object(agent, "llm_settings", return_value=SETTINGS)
    @patch.object(agent.requests, "post")
    def test_errors(self, post, settings):
        for response in [self.request([], 401), self.request([event({"error": {"message": "private"}})]),
                         self.request([event({"choices": [{"delta": {"content": "partial"}}]})]),
                         self.request(["data: [DONE]"]), self.request(["data: invalid"])]:
            post.return_value = response
            with self.assertRaises(agent.LLMError) as error:
                agent.call_llm([])
            self.assertNotIn("offline-test", str(error.exception))
        post.side_effect = requests.Timeout("private")
        result = agent.run_agent("B01228", [])
        self.assertIn("超时", result["response"])
        self.assertNotIn("private", result["response"])

    @patch.object(agent.requests, "post")
    def test_no_key_and_bad_data_do_not_request(self, post):
        with patch.object(agent, "llm_settings", return_value={**SETTINGS, "api_key": None}):
            result = agent.run_agent("B01228", [])
            self.assertIn("尚未配置", result["response"])
        with patch.object(agent, "llm_settings", return_value=SETTINGS):
            result = agent.run_agent("比较 2026-10-01 到 2026-10-13", [])
            self.assertIsNotNone(result["context"].error)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
