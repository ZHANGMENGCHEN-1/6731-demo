"""启动：python -m streamlit run app.py"""
import streamlit as st
import importlib
import inspect
import agent
from analysis import discover_snapshots, load_snapshot, compare_snapshots, top_changes, make_summary

# 热更新 app.py 时，长时间运行的 Streamlit 进程可能仍缓存旧版 agent。
# 仅在检测到旧函数签名时重载，正常 rerun 不重复重载模块。
if "on_text" not in inspect.signature(agent.run_agent).parameters:
    importlib.invalidate_caches()
    importlib.reload(agent)
from agent import run_agent, is_llm_configured
from ui import apply_styles, render_notice

st.set_page_config(page_title="06731持仓监控看板", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
if "page" not in st.session_state:
    st.session_state.page = "📊 CCASS Dashboard"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_runs" not in st.session_state:
    st.session_state.agent_runs = []


def change_page(page):
    st.session_state.page = page


def clear_chat():
    st.session_state.messages = []
    st.session_state.agent_runs = []


page = st.session_state.page
apply_styles(assistant=page == "💬 AI 对话助手")
if page == "💬 AI 对话助手":
    st.button("返回主看板", key="back_dashboard", icon=":material/arrow_back:",
              on_click=change_page, args=("📊 CCASS Dashboard",))
else:
    with st.container(key="top_navigation"):
        columns = st.columns(4)
        for column, label, target, key in (
            (columns[0], "主看板", "📊 CCASS Dashboard", "nav_dashboard"),
            (columns[1], "机构持仓追踪", "Participant 追踪", "nav_participant"),
            (columns[2], "区间对比", "区间对比", "nav_comparison"),
            (columns[3], "查册校验", "查册校验", "nav_registry"),
        ):
            column.button(label, key=key, width="stretch", type="primary" if page == target else "secondary",
                          on_click=change_page, args=(target,))
with st.sidebar:
    st.html('<div class="cc-brand"><div class="cc-brand-icon">◈</div><div><strong>CCASS</strong><small>06731 · WORKSPACE</small></div></div>')
    st.html('<div class="cc-section">AI工具</div>')
    st.button("AI 对话助手", key="nav_assistant", icon=":material/chat_bubble_outline:", width="stretch",
              type="primary" if page == "💬 AI 对话助手" else "secondary",
              on_click=change_page, args=("💬 AI 对话助手",))
    st.divider()
    dates_available = list(discover_snapshots())
    latest = str(dates_available[-1]) if dates_available else "暂无数据"
    data_status = "本地数据已就绪" if dates_available else "等待本地数据"
    st.html(f'<div class="cc-status"><strong>● {data_status}</strong><p>最新快照 · {latest}</p><p>{len(dates_available)} 个日期 · 06731</p></div>')
    if page == "💬 AI 对话助手":
        st.button("清空对话", key="clear_chat", icon=":material/delete_outline:", width="stretch", on_click=clear_chat)
    with st.expander("开发设置"):
        debug = st.checkbox("显示 Agent Debug", value=False, key="agent_debug")
        st.caption("智谱已配置 · Python 数据工具 + LLM 解读" if is_llm_configured() else "LLM 尚未配置 · 当前仅执行本地 Python 工具")
    st.caption("CCASS 持仓观察 · 内部研究 Demo")


def render_assistant(typed=None):
    llm_status = "智谱 GLM 已配置" if is_llm_configured() else "LLM 尚未配置"
    st.html('''<div class="cc-hero">
    <h1>06731 CCASS AI 对话助手</h1>
    <p>通过自然语言查询 06731 上市后的 CCASS 持仓变化</p>
    <span class="cc-badge">框架已就绪 · STATUS</span></div>'''.replace("STATUS", llm_status))
    render_notice()
    snapshot_dates = list(discover_snapshots())
    latest_label = f"{snapshot_dates[-1].month} 月 {snapshot_dates[-1].day} 日" if snapshot_dates else "最新数据日期"
    questions = ["6731 上市以来筹码主要流向哪里？", "最近哪个 Participant 增持最多？", "谁在持续减持？",
                 f"帮我总结 9 月 29 日到 {latest_label}的主要持仓变化。", "B01228 的持仓趋势怎么样？"]
    selected = None
    with st.expander("从一个问题开始" if not st.session_state.messages else "推荐问题", expanded=not st.session_state.messages):
        st.html('<div class="cc-helper">选择一个问题，或在下方输入你想了解的内容</div>')
        for index, question in enumerate(questions):
            if st.button(question, key=f"suggestion_{index}", width="stretch"):
                selected = question
    question = selected or typed
    assistant_index = 0
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=None if message["role"] == "user" else ":material/auto_awesome:"):
            st.write(message["content"])
            if message["role"] == "assistant":
                result = st.session_state.agent_runs[assistant_index]
                context = result["context"]
                if context.error:
                    st.warning(f"本地工具未完成：{context.error}")
                if debug:
                    with st.expander("Agent Debug"):
                        st.write("用户问题：", context.question)
                        st.caption(context.routing_note)
                        st.write("候选工具：", context.candidate_tool)
                        st.json({"participant_id": context.participant_id, "date_range": context.date_range,
                                 "arguments": context.tool_arguments, "dataset_info": context.dataset_info})
                        st.write("工具执行结果（真实 Python 数据，非 LLM 回答）：")
                        if context.error:
                            st.error(context.error)
                        elif hasattr(context.tool_result, "columns"):
                            st.dataframe(context.tool_result, hide_index=True, width="stretch")
                            if context.tool_result.empty:
                                st.caption("结果为空：没有符合当前工具定义的 Participant。")
                        else:
                            st.json(context.tool_result)
                        status = "已请求智谱" if result.get("llm_called") else "未调用 LLM"
                        st.caption(f"已构造 {len(result['llm_messages'])} 条消息 · {status}")
                assistant_index += 1

    if question and question.strip():
        history = [dict(message) for message in st.session_state.messages]
        st.session_state.messages.append({"role": "user", "content": question.strip()})
        with st.chat_message("user"):
            st.write(question.strip())
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            answer = st.empty()
            answer.caption("正在准备数据，等待模型回复…")
            result = run_agent(question, history, on_text=lambda text: answer.markdown(text + " ▍"))
            # 完成后移除光标；若响应中断，使用明确错误替换未完成的正文。
            answer.markdown(result["response"])
        st.session_state.agent_runs.append(result)
        st.session_state.messages.append({"role": "assistant", "content": result["response"]})
        st.rerun()


if page == "💬 AI 对话助手":
    # 必须在主页面根级调用；嵌入 container 会变成普通流式布局，无法固定在屏幕底部。
    typed = st.chat_input("询问持仓变化、Participant 趋势…", key="assistant_input")
    render_assistant(typed)
    st.stop()

import dashboard

# 热更新 app.py 后，进程可能仍持有旧版无参数 dashboard 函数。
if "view" not in inspect.signature(dashboard.render_dashboard).parameters:
    importlib.invalidate_caches()
    importlib.reload(dashboard)

dashboard.render_dashboard(view="主看板" if page == "📊 CCASS Dashboard" else page)
