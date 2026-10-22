"""最近逐笔成交排名，支持 Top 20 / 50 / 100。"""
from datetime import datetime
import socket
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from data_sources import FutuClient, market


@st.cache_data(ttl=30, show_spinner=False)
def load_recent_trades():
    from cloud_store import uses_cloud, get_store
    if uses_cloud():
        frame, record = get_store().read("ticker")
        return frame, record["fetched_at"]
    client = FutuClient()
    with socket.create_connection((client.host, client.port), timeout=1):
        pass
    with client:
        ret, frame = market.get_rt_ticker(client, "HK.06731", num=1000)
    if ret != 0:
        raise ValueError(str(frame))
    return frame, datetime.now(ZoneInfo("Asia/Hong_Kong")).isoformat()


def rank_recent_trades(frame, direction="全部", sort="成交数量", limit=20):
    result = frame.copy()
    if direction != "全部":
        token = {"主动买入": "BUY", "主动卖出": "SELL", "中性": "NEUTRAL"}[direction]
        result = result.loc[result.ticker_direction == token]
    field = "volume" if sort == "成交数量" else "turnover"
    return result.sort_values(field, ascending=False, kind="stable").head(limit).reset_index(drop=True)


def render_trade_ticker():
    st.subheader("最近成交排行")
    st.caption("06731 · 最近最多 1000 笔成交中的排名，不是全天排名。")
    direction_column, sort_column, count_column, refresh = st.columns([2, 2, 1, 1], vertical_alignment="bottom")
    direction = direction_column.selectbox("成交方向", ["全部", "主动买入", "主动卖出", "中性"], key="ticker_direction")
    sort = sort_column.selectbox("排序依据", ["成交数量", "成交金额"], key="ticker_sort")
    limit = count_column.selectbox("展示数量", [20, 50, 100], format_func=lambda n: f"Top {n}", key="ticker_limit")
    if refresh.button("刷新成交", key="ticker_refresh", width="stretch"):
        load_recent_trades.clear()
    try:
        with st.spinner("正在获取最近逐笔成交…"):
            frame, fetched_at = load_recent_trades()
    except Exception as exc:
        from cloud_store import uses_cloud
        st.warning("云端逐笔成交暂不可用，请检查本机采集程序是否已同步样本。" if uses_cloud()
                   else "逐笔成交暂不可用，请确认 OpenD 已启动、登录且具备行情权限。")
        with st.expander("错误详情"):
            st.code(str(exc), language=None)
        return
    if frame.empty:
        st.caption("接口未返回最近成交记录。")
        return
    times = pd.to_datetime(frame.time, errors="coerce")
    from cloud_store import uses_cloud
    if uses_cloud():
        synced = datetime.fromisoformat(fetched_at).astimezone(ZoneInfo("Asia/Hong_Kong"))
        st.caption(f"Supabase 样本最近同步：{synced:%Y-%m-%d %H:%M:%S}（香港时间）；刷新仅重读云端。")
        if (datetime.now(ZoneInfo("Asia/Hong_Kong")) - synced).total_seconds() > 180:
            st.warning("样本同步已超过3分钟，以下为上次成功采集的成交记录。")
    st.caption(f"样本共 {len(frame)} 笔 · 成交时间 {times.min()} → {times.max()} · 香港时间"
               f" · 取数 {datetime.fromisoformat(fetched_at).astimezone(ZoneInfo('Asia/Hong_Kong')):%Y-%m-%d %H:%M:%S}")
    ranked = rank_recent_trades(frame, direction, sort, limit=limit)
    view = ranked[["price", "volume", "turnover", "time", "ticker_direction", "sequence", "type"]].copy()
    view["ticker_direction"] = view.ticker_direction.map({"BUY": "主动买入", "SELL": "主动卖出", "NEUTRAL": "中性"}).fillna(view.ticker_direction)
    view = view.rename(columns={"price": "价格（HKD）", "volume": "数量（股）", "turnover": "金额（HKD）",
                                "time": "成交时间", "ticker_direction": "方向", "sequence": "逐笔序号", "type": "成交类型"})
    view.insert(0, "序号", range(1, len(view) + 1))
    if view.empty:
        st.caption("最近样本中没有符合所选方向的成交。")
    styled = view.style.set_properties(**{"background-color": "#fff", "color": "#171717"}).format(
        {"价格（HKD）": "{:.3f}", "数量（股）": "{:,.0f}", "金额（HKD）": "{:,.2f}"})
    styled = styled.map(lambda value: "color:#d64b50" if value == "主动买入" else "color:#25845e" if value == "主动卖出" else "color:#25282c", subset=["方向"])
    st.dataframe(styled, hide_index=True, width="stretch", height=470)
    st.caption("方向为行情接口的逐笔方向标记，不代表券商或投资者身份。成交时间范围以接口实际返回为准，无法在此指定历史日期。")
    st.download_button(f"下载当前 Top {limit} 原始 CSV", ranked.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"06731_recent_trades_top{limit}.csv", mime="text/csv", disabled=ranked.empty)
    with st.expander("查看完整最近成交样本"):
        st.dataframe(frame.style.set_properties(**{"background-color": "#fff", "color": "#171717"}), hide_index=True, width="stretch")
        st.download_button("下载全部样本 CSV", frame.to_csv(index=False).encode("utf-8-sig"),
                           file_name="06731_recent_trades_sample.csv", mime="text/csv")
