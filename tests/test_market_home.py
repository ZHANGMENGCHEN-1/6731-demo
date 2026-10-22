"""主看板离线验证：正负榜排序、缺失值、服务不可用和页面交互。"""
from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from views.market_home import HK, number, split_brokers, net_volume_ratio, prepare_intraday, intraday_chart


class MarketHomeTests(unittest.TestCase):
    def test_net_volume_ratio(self):
        self.assertEqual(net_volume_ratio(100, 1000), 10)
        self.assertEqual(net_volume_ratio(-200, 1000), -20)
        for total in (0, None, float("nan"), float("inf"), -1):
            self.assertIsNone(net_volume_ratio(100, total))

    def test_intraday_price_volume_and_placeholders(self):
        frame = pd.DataFrame({
            "time": ["2026-10-22 09:32:00", "2026-10-22 09:30:00", "2026-10-22 09:31:00"],
            "cur_price": [39, 38, 0], "volume": [200, 100, 0],
            "is_blank": [False, False, True],
        })
        prices = prepare_intraday(frame)
        self.assertEqual(prices.volume.tolist(), [100, 200])
        self.assertEqual(prices.direction.tolist(), ["平盘", "上涨"])
        spec = intraday_chart(prices).to_dict()
        self.assertEqual(spec["autosize"]["type"], "fit-x")
        self.assertEqual(spec["autosize"]["contains"], "padding")
        self.assertEqual(spec["resolve"]["scale"]["y"], "independent")
        self.assertEqual(spec["layer"][1]["encoding"]["y"]["field"], "volume")
        self.assertEqual(spec["layer"][1]["encoding"]["y"]["scale"]["range"], [330, 250])
        self.assertNotIn("aggregate", spec["layer"][1]["encoding"]["y"])
        color_domain = spec["layer"][1]["encoding"]["color"]["scale"]["domain"]
        self.assertEqual(color_domain, ["上涨", "下跌", "平盘"])
        self.assertTrue(set(prices.direction).issubset(color_domain))
        price_scale = spec["layer"][0]["encoding"]["y"]["scale"]
        for layer in spec["layer"][5:7]:
            self.assertEqual(layer["encoding"]["y"]["scale"], price_scale)
        self.assertLess(price_scale["domain"][0], prices.cur_price.min())
        self.assertGreater(price_scale["domain"][1], prices.cur_price.max())
        self.assertTrue(prepare_intraday(frame.drop(columns="volume")).volume.isna().all())

    def test_rank_direction_and_nulls(self):
        frame = pd.DataFrame({"net_vol": [10, -30, 20, 0, -5, None],
                              "broker_name": list("abcdef")})
        buys, sells = split_brokers(frame)
        self.assertEqual(buys.net_vol.tolist(), [20, 10])
        self.assertEqual(sells.net_vol.tolist(), [-30, -5])
        self.assertEqual(number(float("nan")), "—")

    def test_disconnected_app_still_renders_local_views(self):
        with patch("views.market_home.load_market_home", return_value={"errors": {"connection": "offline"}}), \
             patch("auto_ccass.start_auto_update", return_value={"running": False, "finished_at": None, "error": None}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20).run()
            self.assertFalse(app.exception)
            self.assertTrue(any("行情服务暂不可用" in item.value for item in app.warning))
            app.button(key="nav_ccass_changes").click().run()
            self.assertFalse(app.exception)
            app.button(key="nav_broker_history").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.date_input), 1)
            with patch("views.trade_ticker.render_trade_ticker") as render_trades:
                app.button(key="nav_trade_ticker").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["participant_workspace_view"], "recent_trades")
                render_trades.assert_called_once()
            app.button(key="nav_comparison").click().run()
            self.assertFalse(app.exception)

    def test_data_and_raw_export_render(self):
        now = datetime.now(HK)
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        fixture = {
            "errors": {}, "fetched_at": now.isoformat(),
            "snapshot": pd.DataFrame([dict(name="TEST", last_price=38, prev_close_price=40,
                volume=1000, turnover=38000, high_price=40, low_price=37,
                open_price=39, update_time=timestamp)]),
            "brokers": pd.DataFrame([dict(broker_name="BUY", net_vol=100, is_real_time=True, data_time_str=timestamp),
                dict(broker_name="SELL", net_vol=-200, is_real_time=True, data_time_str=timestamp)]),
            "intraday": pd.DataFrame({"time": [timestamp], "cur_price": [38], "volume": [1000]}),
        }
        with patch("views.market_home.load_market_home", return_value=fixture) as loader, \
             patch("views.market_home.st.fragment", wraps=st.fragment) as fragment:
            app = AppTest.from_string("from views.market_home import render_market_home\nrender_market_home()", default_timeout=20).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "38.000")
            self.assertEqual(len(app.dataframe), 2)
            self.assertIsNone(fragment.call_args.kwargs["run_every"])
            app.checkbox(key="market_auto_refresh").check().run()
            self.assertFalse(app.exception)
            self.assertEqual(fragment.call_args.kwargs["run_every"], 60)
            app.checkbox(key="market_auto_refresh").uncheck().run()
            self.assertIsNone(fragment.call_args.kwargs["run_every"])
            app.button[0].click().run()
            loader.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
