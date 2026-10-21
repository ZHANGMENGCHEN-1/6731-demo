"""06731 主看板：行情与当日券商净买卖；不生成分析结论。"""
from datetime import datetime
from html import escape
import math
import socket
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from data_sources import FutuClient, brokers, market

HK = ZoneInfo("Asia/Hong_Kong")
CODE = "HK.06731"
BUY = "#287568"
SELL = "#913e55"


@st.cache_data(ttl=30, show_spinner=False)
def load_market_home():
    """只缓存数据，不缓存连接；各接口失败分别展示。"""
    result = {"fetched_at": datetime.now(HK).isoformat(), "errors": {}}
    client = FutuClient()
    try:
        with socket.create_connection((client.host, client.port), timeout=1):
            pass
        with client:
            for key, fetch in (
                ("snapshot", lambda: market.get_market_snapshot(client, CODE)),
                ("brokers", lambda: brokers.get_top_ten_buy_sell_brokers(client, CODE, days_before=0)),
                ("intraday", lambda: market.get_rt_data(client, CODE)),
            ):
                try:
                    ret, data = fetch()
                    if ret != 0:
                        result["errors"][key] = str(data)
                    else:
                        result[key] = data
                except Exception as exc:
                    result["errors"][key] = str(exc)
    except Exception as exc:
        result["errors"]["connection"] = str(exc)
    return result


def number(value, digits=0, signed=False):
    try:
        value = float(value)
        if not math.isfinite(value):
            return "—"
        return format(value, f"{'+' if signed else ''},.{digits}f")
    except (TypeError, ValueError):
        return "—"


def split_brokers(frame):
    """只展示接口已返回的正负净量，分别排序，不补全未上榜券商。"""
    if frame is None or frame.empty:
        return pd.DataFrame(), pd.DataFrame()
    if not {"net_vol", "broker_name"}.issubset(frame.columns):
        raise ValueError("券商数据缺少 net_vol / broker_name 字段")
    volumes = pd.to_numeric(frame["net_vol"], errors="coerce")
    return (frame.loc[volumes > 0].sort_values("net_vol", ascending=False),
            frame.loc[volumes < 0].sort_values("net_vol", ascending=True))


def source_time(frame, field):
    if frame is None or frame.empty or field not in frame:
        return "未提供"
    values = frame[field].dropna().astype(str)
    return " / ".join(values.unique()) if not values.empty else "未提供"


def render_leader(frame, title, color):
    if frame.empty:
        st.metric(title, "—")
        st.caption("当前没有可展示的对应方向数据")
        return
    leader = frame.iloc[0]
    ties = frame.loc[frame.net_vol == leader.net_vol]
    names = "、".join(ties.broker_name.astype(str))
    st.html(f'<div class="mh-leader" style="--rank-color:{color}">'
            f'<div class="mh-kicker">{escape(title)}</div>'
            f'<h3>{escape(names)}</h3><div class="mh-leader-value">'
            f'{number(leader.net_vol, signed=True)} <small>股</small></div>'
            f'<p>净买卖量 · 当日累计{" · 并列" if len(ties) > 1 else ""}</p></div>')


def render_ranking(frame, title, color, limit):
    with st.container(border=True):
        st.markdown(f"#### {title}")
        if frame.empty:
            st.info("暂无对应方向数据。")
            return
        maximum = float(frame.net_vol.abs().max())
        rows = []
        for position, (_, row) in enumerate(frame.head(limit).iterrows(), 1):
            percent = abs(float(row.net_vol)) / maximum * 100
            rows.append(
                f'<div class="mh-rank-row"><span class="mh-rank-number">{position:02}</span>'
                f'<div class="mh-rank-body"><div class="mh-rank-label">'
                f'<span>{escape(str(row.broker_name))}</span>'
                f'<strong>{number(row.net_vol, signed=True)}</strong></div>'
                f'<div class="mh-track"><div style="width:{percent:.3f}%;background:{color}"></div>'
                '</div></div></div>')
        st.html('<div class="mh-rank-list">' + "".join(rows) + '</div>')


def render_market_content(status=None):
    with st.spinner("正在获取行情与券商数据…"):
        data = load_market_home()
    errors = data["errors"]
    if "connection" in errors:
        if status is not None:
            status.caption("行情服务暂不可用 · 香港时间")
        st.warning("行情服务暂不可用，请确认 OpenD 已启动并登录，再点击刷新。")
        with st.expander("查看连接详情"):
            st.code(errors["connection"], language=None)
        return
    fetched = datetime.fromisoformat(data["fetched_at"])
    snapshot = data.get("snapshot")
    target = status if status is not None else st
    target.html(
        '<div class="mh-update-strip">'
        f'<div><span>本次取数</span><time>{fetched:%Y-%m-%d %H:%M:%S}</time></div>'
        f'<div><span>行情更新</span><time>{escape(source_time(snapshot, "update_time"))}</time></div>'
        '</div>'
    )
    if snapshot is not None and not snapshot.empty:
        row = snapshot.iloc[0]
        last, previous = row.get("last_price"), row.get("prev_close_price")
        change = pct = None
        if pd.notna(last) and pd.notna(previous) and float(previous) > 0:
            change = float(last) - float(previous)
            pct = change / float(previous) * 100
        a, b, c, d = st.columns([1.6, 1, 1, 1])
        delta = f"{number(change, 3, True)} ({number(pct, 2, True)}%)" if change is not None else None
        with a:
            with st.container(key="latest_quote_card"):
                price, reference = st.columns([1.35, 1], gap="small", vertical_alignment="center")
                price.metric("最新价 · HKD", number(last, 3), delta=delta, delta_color="inverse")
                with reference:
                    st.html('<div class="mh-price-reference">'
                            f'<div><span>今开</span><strong>{number(row.get("open_price"), 3)}</strong></div>'
                            f'<div><span>昨收</span><strong>{number(previous, 3)}</strong></div>'
                            '</div>')
        b.metric("成交额 · HKD", number(row.get("turnover")))
        c.metric("成交量 · 股", number(row.get("volume")))
        d.metric("最高 / 最低 · HKD", f"{number(row.get('high_price'), 3)} / {number(row.get('low_price'), 3)}")
    else:
        st.warning("行情快照暂不可用，券商榜单仍可独立查看。")

    raw_brokers = data.get("brokers")
    broker_frame = raw_brokers
    st.html('<div class="mh-broker-section-label">'
            f'今日券商净买卖 · 数据截至 {escape(source_time(broker_frame, "data_time_str"))} · 单位：股'
            '</div>')
    if broker_frame is not None and not broker_frame.empty:
        if "is_real_time" not in broker_frame or not broker_frame.is_real_time.eq(True).all():
            st.warning("接口未返回实时榜单，暂不展示为今日实时数据。")
            broker_frame = None
        else:
            dates = pd.to_datetime(broker_frame.data_time_str, errors="coerce").dt.date
            if dates.isna().any() or not dates.eq(datetime.now(HK).date()).all():
                st.warning("以下为接口最近可用交易日数据，并非今天；请以数据更新时间为准。")
    try:
        buys, sells = split_brokers(broker_frame)
    except ValueError as exc:
        st.error(str(exc))
        buys, sells = pd.DataFrame(), pd.DataFrame()
    left, right = st.columns(2)
    with left:
        render_leader(buys, "净买入最多", BUY)
    with right:
        render_leader(sells, "净卖出最多", SELL)

    control, hint = st.columns([1, 3])
    with control:
        limit = st.segmented_control("展示数量", [5, 10], default=5,
                                     format_func=lambda value: f"Top {value}", key="broker_rank_count",
                                     label_visibility="collapsed") or 5
    with hint:
        st.caption("净买卖为当日累计；条长按各榜最大净量分别缩放。")
    chart, buy_column, sell_column = st.columns([1.15, 1, 1], gap="small")
    with chart:
        with st.container(border=True, key="intraday_panel"):
            st.html('<div class="mh-chart-heading" role="heading" aria-level="4">当日分时</div>')
            intraday = data.get("intraday")
            if intraday is not None and not intraday.empty and {"time", "cur_price"}.issubset(intraday):
                prices = intraday[["time", "cur_price"]].copy()
                prices["time"] = pd.to_datetime(prices.time, errors="coerce")
                prices["cur_price"] = pd.to_numeric(prices.cur_price, errors="coerce")
                prices = prices.dropna().sort_values("time")
                st.line_chart(prices, x="time", y="cur_price", color="#803b4b", height=190,
                              x_label="香港时间", y_label="价格（HKD）")
                st.caption(f"分时数据截至：{prices.time.max() if not prices.empty else '暂无'}")
            else:
                st.info("暂无分时数据，行情权限不足或未开市时可能无法获取。")
    with buy_column:
        render_ranking(buys, "净买入榜", BUY, limit)
    with sell_column:
        render_ranking(sells, "净卖出榜", SELL, limit)
    st.caption("券商榜单为经纪渠道成交汇总，不代表持仓或自营交易；休市时可能返回最近交易日数据。")


def render_raw_data(data):
    """卡片外保留原始数据；页面完整重跑时读取同一缓存快照。"""
    if "connection" in data["errors"]:
        return
    fetched = datetime.fromisoformat(data["fetched_at"])
    raw_brokers, snapshot = data.get("brokers"), data.get("snapshot")
    with st.expander("原始数据与字段", key="raw_market_data"):
        st.caption("页面数据最多缓存 30 秒；金额和价格以港元计，数量以股计。")
        st.caption("原始字段未改名；券商数据为接口返回的十大净买入 / 净卖出名单，并非全部券商。")
        for title, frame in [("券商净买卖", raw_brokers), ("行情快照", snapshot)]:
            st.markdown(f"**{title}**")
            if frame is not None:
                st.dataframe(frame.style.set_properties(**{
                    "background-color": "#ffffff", "color": "#171717",
                }), hide_index=True, width="stretch")
                st.download_button(f"下载{title} CSV", frame.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"06731_{title}_{fetched:%Y%m%d_%H%M%S}.csv", mime="text/csv")
        st.markdown("[富途接口文档](https://openapi.futunn.com/futu-api-doc/quote/get-top-ten-buy-sell-brokers.html)")
        for key, error in data["errors"].items():
            st.warning(f"{key} 获取失败：{error}")


def render_market_home():
    st.html('''<style>
    .stMainBlockContainer:has(.mh-stock-title), .stMainBlockContainer:has(.mh-home-marker) {max-width:1600px;padding-top:64px;padding-bottom:.8rem;}
    [data-testid="stElementContainer"]:has(.mh-home-marker) {display:none;}
    .stMainBlockContainer:has(.mh-home-marker) > [data-testid="stVerticalBlock"] {gap:0;}
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stVerticalBlock"] {gap:.65rem;}
    .stMainBlockContainer:has(.mh-home-marker) .st-key-top_navigation {padding:4px 24px 0 60px;margin:0;}
    .st-key-market_section {background:#fff;border:1px solid #e6e0d8;border-radius:12px;padding:18px 20px;box-shadow:0 2px 10px rgba(37,40,44,.025);}
    .st-key-market_section [data-testid="stMetric"] {background:#fff!important;}
    .st-key-market_section .mh-leader {background:#fff;}
    .st-key-raw_market_data [data-testid="stExpanderDetails"] {background:#fff;}
    .st-key-raw_market_data [data-testid="stDataFrame"] {
        background:#fff;border:1px solid #cbd1d8;border-radius:8px;
        box-shadow:0 2px 5px rgba(25,35,45,.06);overflow:hidden;
        --gdg-bg-cell:#fff;--gdg-bg-header:#e8edf2;
        --gdg-bg-header-hovered:#dde4eb;--gdg-border-color:#d3dae2;
        --gdg-text-dark:#171717;--gdg-text-header:#303740;
    }
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stHeadingWithActionElements"] h1 {font-size:22px;line-height:1.2;padding:0;}
    .stMainBlockContainer:has(.mh-home-marker) h4 {font-size:15px;padding:0;margin:0;}
    .mh-chart-heading {display:block;box-sizing:border-box;min-height:38px;padding:2px 0 12px;font-size:15px;font-weight:600;line-height:24px;}
    .stMainBlockContainer .st-key-intraday_panel [data-testid="stVerticalBlock"] {gap:1rem;}
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stMetric"] {padding:9px 12px;border-top-width:2px;}
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stMetricValue"],
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stMetricValue"] * {font-size:32px!important;font-weight:700!important;line-height:1.25;}
    .st-key-latest_quote_card {background:#fff;border:1px solid #d4ccc2;border-top:2px solid #a68a62;border-radius:10px;padding:9px 12px;}
    .stMainBlockContainer:has(.mh-home-marker) .st-key-latest_quote_card [data-testid="stMetric"] {border:0;padding:0;border-radius:0;}
    .mh-price-reference {font-size:12px;line-height:1.8;font-variant-numeric:tabular-nums;}
    .mh-price-reference div {display:flex;flex-wrap:wrap;gap:4px 10px;justify-content:space-between;}
    .mh-price-reference span {color:#645f59;}
    .mh-price-reference strong {font-weight:500;}
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stCaptionContainer"],
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stCaptionContainer"] p {color:#171717;font-size:12px;line-height:1.65;margin:2px 0;overflow-wrap:anywhere;}
    .mh-broker-section-label {color:#171717;font-size:12px;line-height:1.7;padding:4px 0 2px;overflow-wrap:anywhere;}
    .stMainBlockContainer:has(.mh-home-marker) .mh-update-strip span,
    .stMainBlockContainer:has(.mh-home-marker) .mh-kicker,
    .stMainBlockContainer:has(.mh-home-marker) .mh-leader p,
    .stMainBlockContainer:has(.mh-home-marker) .mh-price-reference span {color:#171717;}
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stVerticalBlockBorderWrapper"] > div {padding:.65rem;}
    .mh-stock-title {font-size:18px;font-weight:650;margin:2px 0 0;}
    .mh-stock-title span {font-size:12px;color:#645f59;margin-left:12px;font-weight:400;}
    .st-key-market_status_toolbar {padding-bottom:8px;border-bottom:1px solid #ded6cd;margin-bottom:4px;}
    .mh-update-strip {display:flex;flex-wrap:wrap;align-items:center;gap:6px 24px;padding:4px 0;font-size:12px;line-height:1.65;}
    .mh-update-strip > div {display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px;}
    .mh-update-strip span {color:#72685f;}
    .mh-update-strip time {font-variant-numeric:tabular-nums;color:#34312e;white-space:nowrap;}
    .mh-update-strip .mh-refresh-mode {margin-left:auto;gap:12px;color:#645f59;}
    .mh-leader {background:#fff;border:1px solid #d4ccc2;border-left:3px solid var(--rank-color);border-radius:8px;padding:12px 16px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 18px;align-items:center;}
    .mh-kicker {font-size:12px;color:#645f59;letter-spacing:1px;}
    .mh-leader h3 {font-size:15px!important;margin:0!important;padding:0;overflow-wrap:anywhere;grid-column:1;grid-row:2;}
    .mh-leader-value {color:var(--rank-color);font-size:25px;font-weight:700;font-variant-numeric:tabular-nums;grid-column:2;grid-row:1 / 3;}
    .mh-leader-value small {font-size:13px;font-weight:400;}
    .mh-leader p {font-size:11px;line-height:1.6;color:#645f59;margin:0;grid-column:1 / 3;}
    .mh-rank-list {max-height:236px;overflow-y:auto;padding-right:4px;}
    .mh-rank-row {display:flex;gap:8px;padding:9px 0;border-bottom:1px solid #eee8df;}
    .mh-rank-number {color:#918377;font-size:12px;padding-top:2px;min-width:20px;}
    .mh-rank-body {flex:1;min-width:0;}
    .mh-rank-label {display:flex;align-items:baseline;gap:12px;justify-content:space-between;font-size:13px;line-height:1.5;margin-bottom:6px;}
    .mh-rank-label span {overflow-wrap:anywhere;}
    .mh-rank-label strong {white-space:nowrap;font-variant-numeric:tabular-nums;}
    .mh-track {height:3px;background:#eee8df;border-radius:4px;overflow:hidden;}
    .mh-track div {height:100%;border-radius:4px;}
    .stMainBlockContainer:has(.mh-home-marker) h4,
    .mh-chart-heading,.mh-leader h3 {font-size:var(--cc-title-size,16px)!important;font-weight:600;line-height:1.5;}
    .mh-price-reference,.mh-broker-section-label,.mh-stock-title span,
    .mh-update-strip,.mh-kicker,.mh-leader p,.mh-rank-number,.mh-rank-label,
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stCaptionContainer"],
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stCaptionContainer"] p {font-size:var(--cc-text-size,13px)!important;line-height:1.65;}
    @media(max-width:800px) {.mh-leader {display:block;} .mh-leader-value {font-size:22px;} .mh-rank-label {flex-wrap:wrap;} }
    </style>''')
    st.html('<span class="mh-home-marker"></span>')
    with st.container(key="market_section"):
        render_market_section()
    render_raw_data(load_market_home())


def render_market_section():
    with st.container(key="market_status_toolbar"):
        times, controls = st.columns([2.3, 1.2], gap="small", vertical_alignment="center")
        with times:
            status = st.empty()
        with controls:
            with st.container(key="market_refresh_toolbar", horizontal=True,
                              horizontal_alignment="right", vertical_alignment="center", gap="small"):
                auto = st.checkbox("每 60 秒自动刷新", value=False, key="market_auto_refresh",
                                   help="香港时间。页面保持连接时每60秒重新获取行情快照、当日券商榜单和分时数据；上游未更新时数值可能不变。")
                if st.button("刷新数据", icon=":material/refresh:", width="content"):
                    load_market_home.clear()
    st.fragment(run_every=60 if auto else None)(render_market_content)(status=status)
