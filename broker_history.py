"""按明确日期查询券商净买卖；日期转换在页面服务层完成。"""
from datetime import date, datetime, timedelta
import socket
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from data_sources import FutuClient, brokers

HK = ZoneInfo("Asia/Hong_Kong")
CODE = "HK.06731"


def response_date(frame):
    if not isinstance(frame, pd.DataFrame) or frame.empty or "data_time_str" not in frame:
        raise ValueError("接口未返回可核对日期的数据。")
    days = pd.to_datetime(frame.data_time_str, errors="coerce").dt.date
    if days.isna().any() or days.nunique() != 1:
        raise ValueError("接口数据日期缺失或不一致，未展示结果。")
    return days.iloc[0]


def query_brokers_on_date(client, target):
    """先确定接口实际基准日，再按交易日历换算；拒绝错日结果。"""
    ret, latest = brokers.get_top_ten_buy_sell_brokers(client, CODE, days_before=0)
    if ret != 0:
        raise ValueError(f"获取券商基准日期失败：{latest}")
    anchor = response_date(latest)
    if target > anchor:
        raise ValueError(f"所选日期尚无数据，接口最近可用日期为 {anchor}。")
    ret, calendar = client.call("request_trading_days", code=CODE,
                                start=target.isoformat(), end=anchor.isoformat())
    if ret != 0:
        raise ValueError(f"港股交易日历查询失败：{calendar}")
    trading_days = sorted({date.fromisoformat(item["time"]) for item in calendar})
    if target not in trading_days:
        raise ValueError(f"{target} 不在返回的港股交易日历中，不替换为相邻交易日。")
    if anchor not in trading_days:
        raise ValueError("券商基准日期与交易日历不一致，请稍后重试。")
    offset = trading_days.index(anchor) - trading_days.index(target)
    if offset:
        ret, frame = brokers.get_top_ten_buy_sell_brokers(client, CODE, days_before=offset)
        if ret != 0:
            raise ValueError(f"历史券商查询失败：{frame}")
    else:
        frame = latest
    actual = response_date(frame)
    if actual != target:
        raise ValueError(f"日期校验未通过：请求 {target}，接口实际返回 {actual}。未展示错日数据。")
    return {"date": target, "anchor": anchor, "days_before": offset,
            "frame": frame, "fetched_at": datetime.now(HK).isoformat()}


def render_broker_history():
    st.html('<style>.st-key-broker_history {background:#fff;border:1px solid #e6e0d8;'
            'border-radius:12px;padding:18px 20px;margin-top:16px;}</style>')
    with st.container(key="broker_history"):
        st.caption("06731 · 按指定日期查询十大净买入 / 净卖出券商。")
        today = datetime.now(HK).date()
        with st.form("broker_history_query"):
            day_column, action = st.columns([3, 1], vertical_alignment="bottom")
            target = day_column.date_input("查询日期", value=max(date(2026, 9, 29), today - timedelta(days=1)),
                                           min_value=date(2026, 9, 29), max_value=today)
            submitted = action.form_submit_button("查询券商数据", width="stretch")
            st.caption("非交易日不自动顺延；选择今日返回盘中累计，历史日期仅提供净量和券商名称。")
        if submitted:
            st.session_state.pop("broker_history_result", None)
            try:
                with st.spinner("正在查询交易日历和券商数据…"):
                    client = FutuClient()
                    with socket.create_connection((client.host, client.port), timeout=1):
                        pass
                    with client:
                        result = query_brokers_on_date(client, target)
                st.session_state.broker_history_result = result
            except Exception as exc:
                st.error(f"查询未完成：{exc}")
        result = st.session_state.get("broker_history_result")
        if result is None:
            return
        frame = result["frame"]
        st.markdown(f"**查询结果 · {result['date']}**")
        st.caption(f"已核对接口返回日期 · days_before={result['days_before']} · 基准日 {result['anchor']}"
                   f" · 取数时间 {datetime.fromisoformat(result['fetched_at']):%Y-%m-%d %H:%M:%S}（香港时间）")
        if result["date"] == today:
            st.info("当前选择的是今日，以下为截至接口更新时间的累计数据，并非收盘汇总。")
        buy_column, sell_column = st.columns(2)
        volumes = pd.to_numeric(frame.net_vol, errors="coerce")
        for column, title, rows in (
            (buy_column, "净买入券商", frame.loc[volumes > 0].sort_values("net_vol", ascending=False)),
            (sell_column, "净卖出券商", frame.loc[volumes < 0].sort_values("net_vol")),
        ):
            with column:
                st.markdown(f"**{title} · 股**")
                if rows.empty:
                    st.caption("该日没有返回对应方向的券商记录。")
                else:
                    st.dataframe(rows[["broker_name", "net_vol"]].style.set_properties(**{
                        "background-color": "#fff", "color": "#171717"}), hide_index=True, width="stretch")
        with st.expander("查看完整原始字段"):
            st.dataframe(frame.style.set_properties(**{"background-color": "#ffffff", "color": "#171717"}),
                         hide_index=True, width="stretch")
        st.download_button("下载该日原始 CSV", frame.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"06731_brokers_{result['date']}.csv", mime="text/csv")
        st.caption("名单仅含接口返回的十大净买入 / 净卖出渠道；未上榜不代表零交易，净买卖不等于持仓变化。")
