"""06731 主看板：行情与当日券商净买卖；不生成分析结论。"""
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from html import escape
import math
import socket
from zoneinfo import ZoneInfo

import pandas as pd
import altair as alt
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
    from cloud_store import uses_cloud, get_store
    if uses_cloud():
        result["backend"] = "supabase"
        store = get_store()
        with ThreadPoolExecutor(max_workers=3) as pool:
            pending = {dataset: pool.submit(store.read, dataset)
                       for dataset in ("snapshot", "brokers", "intraday")}
            for dataset, future in pending.items():
                try:
                    frame, record = future.result()
                    result[dataset] = frame
                    result.setdefault("sync_times", {})[dataset] = record["fetched_at"]
                    if dataset == "snapshot":
                        result["fetched_at"] = record["fetched_at"]
                except ValueError as exc:
                    result["errors"][dataset] = str(exc)
        if not any(key in result for key in ("snapshot", "brokers", "intraday")):
            result["errors"]["connection"] = "云端尚无可读取的行情，请检查同步程序和 Supabase 配置。"
        return result
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


def net_volume_ratio(net_volume, outstanding_shares):
    """带方向的净量占流通股本比例；缺失或零股本不计算。"""
    try:
        net_volume, outstanding_shares = float(net_volume), float(outstanding_shares)
        if math.isfinite(net_volume) and math.isfinite(outstanding_shares) and outstanding_shares > 0:
            return net_volume / outstanding_shares * 100
    except (TypeError, ValueError):
        pass
    return None


def prepare_intraday(frame):
    prices = frame.copy()
    if "is_blank" in prices:
        prices = prices.loc[~prices.is_blank.fillna(False).astype(bool)].copy()
    prices["time"] = pd.to_datetime(prices.time, errors="coerce")
    prices["cur_price"] = pd.to_numeric(prices.cur_price, errors="coerce")
    prices = prices.loc[prices.cur_price.gt(0) & prices.cur_price.lt(float("inf"))]
    prices = prices.dropna(subset=["time", "cur_price"]).sort_values("time")
    prices = prices.drop_duplicates("time", keep="last")
    volume = prices["volume"] if "volume" in prices else pd.Series(index=prices.index, dtype=float)
    prices["volume"] = pd.to_numeric(volume, errors="coerce")
    prices["volume"] = prices.volume.where(prices.volume.ge(0) & prices.volume.lt(float("inf")))
    prices["direction"] = "平盘"
    changes = prices.cur_price.diff()
    prices.loc[changes.gt(0), "direction"] = "上涨"
    prices.loc[changes.lt(0), "direction"] = "下跌"
    return prices[["time", "cur_price", "volume", "direction"]]


def intraday_chart(prices):
    """单一画布内绘制上下价量区，独立纵轴、统一时间和悬停位置。"""
    cursor = alt.selection_point(
        fields=["time"], encodings=["x"], nearest=True,
        on="pointerover", clear="pointerout", empty=False,
    )
    base = alt.Chart(prices).encode(
        x=alt.X("time:T", title="香港时间", axis=alt.Axis(format="%H:%M", tickCount=5))
    )
    tooltip = [alt.Tooltip("time:T", title="时间", format="%H:%M"),
               alt.Tooltip("cur_price:Q", title="价格（HKD）", format=".3f"),
               alt.Tooltip("volume:Q", title="该分时段成交量（股）", format=",.0f")]
    price_axis = alt.Axis(title="价格（HKD）", grid=False, tickCount=5, domain=False)
    low, high = float(prices.cur_price.min()), float(prices.cur_price.max())
    margin = max((high - low) * 0.05, abs(high) * 0.0005, 0.001)
    # 悬停图层筛选后只剩一个点，必须与主价格线固定使用同一数值范围。
    price_scale = alt.Scale(domain=[low - margin, high + margin],
                            zero=False, nice=False, range=[225, 0])
    price = base.mark_line(color="#803b4b", strokeWidth=1.8, clip=True).encode(
        y=alt.Y("cur_price:Q", scale=price_scale, axis=price_axis)
    )
    volume = base.mark_bar(size=2, clip=True).encode(
        y=alt.Y("volume:Q", stack=None,
                scale=alt.Scale(zero=True, range=[330, 250]),
                axis=alt.Axis(title="成交量（股）", orient="right", grid=False,
                              format="~s", tickCount=3, domain=False)),
        y2=alt.value(330),
        color=alt.Color("direction:N", scale=alt.Scale(
            domain=["上涨", "下跌", "平盘"], range=[SELL, BUY, "#a8a29e"]), legend=None),
        tooltip=tooltip,
    )
    # 最近时间点的命中区域贯穿价量区；提示直接使用原始记录，不作求和。
    hover = base.mark_point(opacity=0).encode(y=alt.value(0), tooltip=tooltip).add_params(cursor)
    rule = base.mark_rule(color="#a8a29e", strokeDash=[3, 3]).encode(
        opacity=alt.condition(cursor, alt.value(0.8), alt.value(0)), tooltip=tooltip
    )
    horizontal = base.transform_filter(cursor).mark_rule(
        color="#a8a29e", strokeDash=[3, 3]
    ).encode(
        x=alt.value(0),
        x2=alt.value(alt.ExprRef(expr="width")),
        y=alt.Y("cur_price:Q", scale=price_scale, axis=None),
        tooltip=tooltip,
    )
    selected_point = base.transform_filter(cursor).mark_point(
        color="#803b4b", filled=True, size=35
    ).encode(
        y=alt.Y("cur_price:Q", scale=price_scale, axis=None),
        tooltip=tooltip,
    )
    separator = alt.Chart(pd.DataFrame({"separator": [0]})).mark_rule(
        color="#e6e0d8"
    ).encode(y=alt.value(240))
    return alt.layer(price, volume, separator, hover, rule, horizontal, selected_point).resolve_scale(y="independent").properties(
        width="container", height=330,
        autosize=alt.AutoSizeParams(type="fit-x", contains="padding", resize=True),
        padding={"left": 0, "right": 0, "top": 8, "bottom": 0},
    ).configure_view(stroke=None)


def render_leader(frame, title, color, outstanding_shares=None):
    if frame.empty:
        st.metric(title, "—")
        st.caption("当前没有可展示的对应方向数据")
        return
    leader = frame.iloc[0]
    ties = frame.loc[frame.net_vol == leader.net_vol]
    names = "、".join(ties.broker_name.astype(str))
    ratio = net_volume_ratio(leader.net_vol, outstanding_shares)
    ratio_text = f'{number(ratio, 4, signed=True)}%' if ratio is not None else "—"
    st.html(f'<div class="mh-leader" style="--rank-color:{color}">'
            f'<div class="mh-kicker">{escape(title)}</div>'
            f'<h3>{escape(names)}</h3><div class="mh-leader-figures">'
            f'<div class="mh-leader-value">{number(leader.net_vol, signed=True)} <small>股</small></div>'
            f'<div class="mh-leader-ratio"><strong>{ratio_text}</strong><span>占流通股本</span></div></div>'
            f'<p>净买卖量 · 当日累计{" · 并列" if len(ties) > 1 else ""}</p></div>')


def render_ranking(frame, title, color, limit):
    with st.container(border=True):
        st.markdown(f"#### {title} · Top {limit}")
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
        if len(frame) < limit:
            st.caption(f"当前接口仅返回 {len(frame)} 家符合该方向的券商。")


def render_market_content(status=None):
    with st.spinner("正在获取行情与券商数据…"):
        data = load_market_home()
    errors = data["errors"]
    if "connection" in errors:
        if status is not None:
            status.caption("行情服务暂不可用 · 香港时间")
        st.warning("云端行情暂不可用，请检查本机同步程序与 Supabase 配置。" if data.get("backend") == "supabase"
                   else "行情服务暂不可用，请确认 OpenD 已启动并登录，再点击刷新。")
        with st.expander("查看连接详情"):
            st.code(errors["connection"], language=None)
        return
    fetched = datetime.fromisoformat(data["fetched_at"]).astimezone(HK)
    is_cloud = data.get("backend") == "supabase"
    snapshot = data.get("snapshot")
    target = status if status is not None else st
    target.html(
        '<div class="mh-update-strip">'
        f'<div><span>{"最近同步" if is_cloud else "本次取数"}</span><time>{fetched:%Y-%m-%d %H:%M:%S}</time></div>'
        f'<div><span>行情更新</span><time>{escape(source_time(snapshot, "update_time"))}</time></div>'
        '</div>'
    )
    if is_cloud:
        if (datetime.now(HK) - fetched).total_seconds() > 180:
            st.warning("最近同步已超过3分钟，当前展示上次成功采集的数据，请检查本机采集程序是否仍在运行。")
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
    outstanding_shares = None
    if snapshot is not None and not snapshot.empty and broker_frame is not None and not broker_frame.empty:
        quote_date = pd.to_datetime(snapshot.iloc[0].get("update_time"), errors="coerce")
        broker_dates = pd.to_datetime(broker_frame["data_time_str"], errors="coerce")
        if pd.notna(quote_date) and broker_dates.notna().all() and broker_dates.dt.date.eq(quote_date.date()).all():
            outstanding_shares = snapshot.iloc[0].get("outstanding_shares")
    if not buys.empty or not sells.empty:
        if net_volume_ratio(0, outstanding_shares) is None:
            st.caption("流通股本未提供、无效或与券商数据日期不一致，占比暂不可用。")
    left, right = st.columns(2)
    with left:
        render_leader(buys, "净买入最多", BUY, outstanding_shares)
    with right:
        render_leader(sells, "净卖出最多", SELL, outstanding_shares)

    control, hint = st.columns([1, 3])
    with control:
        limit = st.segmented_control("展示数量", [5, 10], default=5,
                                     format_func=lambda value: f"Top {value}", key="broker_rank_count",
                                     label_visibility="collapsed") or 5
    with hint:
        st.caption("净买卖为当日累计；条长按各榜最大净量分别缩放。")
    chart, buy_column, sell_column = st.columns([1.8, 1, 1], gap="medium")
    with chart:
        with st.container(border=True, key="intraday_panel"):
            st.html('<div class="mh-chart-heading" role="heading" aria-level="4">当日分时</div>')
            intraday = data.get("intraday")
            if intraday is not None and not intraday.empty and {"time", "cur_price"}.issubset(intraday):
                prices = prepare_intraday(intraday)
                if not prices.empty:
                    st.altair_chart(intraday_chart(prices), width="stretch")
                    if prices.volume.isna().all():
                        st.caption("成交量数据暂不可用。")
                else:
                    st.info("暂无有效分时数据。")
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
        background:#fff;border:1px solid #d4ccc2;border-radius:8px;
        box-shadow:0 2px 5px rgba(25,35,45,.06);overflow:hidden;
        --gdg-bg-cell:#fff;--gdg-bg-header:#ebe5dc;
        --gdg-bg-header-hovered:#e2d7c7;--gdg-border-color:#d4ccc2;
        --gdg-text-dark:#171717;--gdg-text-header:#303740;
    }
    .stMainBlockContainer:has(.mh-home-marker) [data-testid="stHeadingWithActionElements"] h1 {font-size:22px;line-height:1.2;padding:0;}
    .stMainBlockContainer:has(.mh-home-marker) h4 {font-size:15px;padding:0;margin:0;}
    .mh-chart-heading {display:block;box-sizing:border-box;min-height:38px;padding:2px 0 12px;font-size:15px;font-weight:600;line-height:24px;}
    .stMainBlockContainer .st-key-intraday_panel [data-testid="stVerticalBlock"] {gap:1rem;}
    .st-key-intraday_panel {min-width:0;overflow:hidden;}
    .st-key-intraday_panel [data-testid="stVegaLiteChart"] {width:100%;min-width:0;max-width:100%;}
    .st-key-intraday_panel .vega-embed {width:100%;min-width:0;max-width:100%;}
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
    .mh-leader-figures {grid-column:2;grid-row:1 / 4;text-align:right;min-width:0;font-variant-numeric:tabular-nums;}
    .mh-leader-value {color:var(--rank-color);font-size:25px;font-weight:700;overflow-wrap:anywhere;}
    .mh-leader-value small {font-size:13px;font-weight:400;}
    .mh-leader-ratio {display:flex;justify-content:flex-end;align-items:baseline;flex-wrap:wrap;gap:4px 8px;margin-top:4px;font-size:12px;}
    .mh-leader-ratio strong {color:var(--rank-color);font-size:16px;}
    .mh-leader-ratio span {color:#645f59;}
    .mh-leader p {font-size:11px;line-height:1.6;color:#645f59;margin:0;grid-column:1;grid-row:3;}
    .mh-rank-list {max-height:355px;overflow-y:auto;scrollbar-gutter:stable;padding-right:4px;}
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
    @media(max-width:1100px) {
        .st-key-market_section [data-testid="stMetricValue"],
        .st-key-market_section [data-testid="stMetricValue"] * {font-size:clamp(18px,2.2vw,28px)!important;}
        .mh-rank-label {flex-wrap:wrap;gap:2px 8px;}
    }
    @media(max-width:800px) {
        .st-key-market_section {padding:12px;}
        .mh-leader {grid-template-columns:minmax(0,1fr);gap:6px;}
        .mh-leader-figures {grid-column:1;grid-row:3;text-align:left;}
        .mh-leader-ratio {justify-content:flex-start;}
        .mh-leader p {grid-row:4;}
        .mh-leader-value {font-size:22px;}
    }
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
