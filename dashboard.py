"""持仓监控首页与原有自定义日期比较；仅使用本地 Python 计算。"""
import pandas as pd
import streamlit as st
from analysis import get_monitoring_data, compare_snapshots, top_changes, make_summary, make_home_summary, PERSISTENT_DEFINITION
from ui import render_notice

LABELS = {"participant_id": "Participant ID", "participant_name": "Participant Name", "address": "地址",
          "start_shares": "起始持仓", "end_shares": "结束持仓", "shares_change": "持仓变化",
          "start_percentage": "起始占比（%）", "end_percentage": "结束占比（%）", "percentage_change": "占比变化（百分点）",
          "direction_count": "同向区间数", "interval_count": "总区间数", "direction_share": "同向变化量占比（%）",
          "window_start": "窗口起日", "window_end": "窗口止日",
          "increase_rank": "增持排名", "decrease_rank": "减持排名"}


def show_table(frame, include_address=False):
    if not include_address:
        frame = frame.drop(columns="address", errors="ignore")
    st.dataframe(frame.rename(columns=LABELS).style.format({
        "起始持仓": "{:,.0f}", "结束持仓": "{:,.0f}", "持仓变化": "{:+,.0f}",
        "起始占比（%）": "{:.2f}", "结束占比（%）": "{:.2f}", "占比变化（百分点）": "{:+.2f}",
        "同向变化量占比（%）": "{:.1f}",
        "增持排名": "{:.0f}", "减持排名": "{:.0f}",
    }, na_rep="—"), hide_index=True, width="stretch")


def show_rankings(comparison, n, prefix):
    increases, decreases = top_changes(comparison)
    left, right = st.columns(2)
    for column, direction, frame, color in ((left, "增持", increases.head(n), "#486888"),
                                             (right, "减持", decreases.head(n), "#a65363")):
        with column:
            st.markdown(f"**{prefix} Top {n} {direction}**")
            if frame.empty:
                st.caption("没有符合条件的 Participant。")
                continue
            chart = frame.assign(label=frame.participant_id + " · " + frame.participant_name)
            chart_tab, detail_tab = st.tabs(["图表", "数据明细"])
            with chart_tab:
                st.bar_chart(chart, x="label", y="shares_change", color=color, x_label="Participant", y_label="持仓变化（股）")
            with detail_tab:
                show_table(frame)


def show_leaders(comparison, title, period):
    st.markdown(f"**{title}** · {period}")
    up, down = top_changes(comparison)
    left, right = st.columns(2)
    for column, frame, direction in ((left, up, "增加"), (right, down, "减少")):
        with column:
            if frame.empty:
                st.metric(f"最大持仓{direction}", "—")
                st.caption("该区间没有符合条件的 Participant。")
            else:
                row = frame.iloc[0]
                st.metric(f"最大持仓{direction}", f"{abs(int(row.shares_change)):,} 股")
                st.write(f"**{row.participant_id}** · {row.participant_name}")


def render_dashboard(view="主看板"):
    try:
        data = get_monitoring_data()
    except (ValueError, OSError, OverflowError) as exc:
        st.error(f"数据读取失败：{exc}")
        return
    dates, frames, workdays = data["dates"], data["frames"], data["workdays"]
    if view != "主看板":
        st.caption(f"最新数据：{dates[-1] if dates else '暂无'} · 已获取 {len(dates)} 个日期")
        render_notice()
        if view == "查册校验":
            show_registry()
        elif not dates:
            st.info("暂无真实 CSV，请先运行 fetch_ccass.py。")
        elif view == "Participant 追踪":
            show_participant_tracking(frames)
        elif view == "区间对比":
            if len(dates) >= 2:
                show_custom_comparison(dates, frames)
            else:
                st.info("至少需要两个真实日期。")
        return
    a, b, c, d = st.columns(4)
    a.metric("股票代码", "06731")
    b.metric("上市日期", "2026-09-29")
    c.metric("最新数据日期", str(dates[-1]) if dates else "暂无")
    d.metric("已获取日期数", len(dates))
    with st.container(border=True, key="home_summary"):
        st.markdown("### 最新持仓变化摘要")
        if data["latest_snapshot_comparison"] is None:
            st.caption("至少需要两个已有日期快照，才能生成变化摘要。")
        else:
            st.caption(f"{dates[-2]} → {dates[-1]} · 最新快照与前一已有快照 · Python 自动汇总")
            for paragraph in make_home_summary(data["latest_snapshot_comparison"]):
                st.write(paragraph)
            st.caption("集中度按持股数量变化的绝对值计算，增加与减少分别统计；样本净变化不等于市场资金净流入或净流出，不能确认机构之间存在直接筹码转移。")
    render_notice()
    with st.expander("数据来源与统计口径", expanded=False):
        st.caption("最新交易日栏目使用最近两个已有周一至周五快照，不额外接入交易所日历；周末快照不作为交易日。上市以来从最早已有快照至最新快照计算。")
        st.markdown("[HKEX 原始查询页面](https://www3.hkexnews.hk/sdw/search/searchsdw.aspx) · 本页面不自动抓取或刷新数据")
    if not dates:
        st.info("暂无真实 CSV，请先运行 fetch_ccass.py。")
        return
    if dates[0].isoformat() != "2026-09-29":
        st.warning(f"上市日快照缺失，上市以来栏目当前以 {dates[0]} 为基准，不代表完整上市以来变化。")
    st.subheader("持仓分析")
    st.caption("概览最新变化、上市以来表现和近期持续趋势；机构详情与自定义对比请使用顶部入口。")
    latest_tab, listing_tab, persistent_tab = st.tabs(["最新变化", "上市以来", "持续趋势"])
    with latest_tab:
        st.subheader("最新交易日 · Top 5")
        if data["latest_comparison"] is not None:
            show_leaders(data["latest_comparison"], "最新交易日", f"{workdays[-2]} → {workdays[-1]}")
            show_rankings(data["latest_comparison"], 5, "最新交易日")
        else:
            st.caption("数据不足，暂不展示排名。")
    with listing_tab:
        st.subheader("上市以来 · Top 10")
        if data["listing_comparison"] is not None:
            show_leaders(data["listing_comparison"], "上市以来", f"{dates[0]} → {dates[-1]}")
            show_rankings(data["listing_comparison"], 10, "上市以来")
        else:
            st.caption("至少需要两个快照。")
    with persistent_tab:
        st.subheader("近期持续增持 / 减持 Participant")
        st.caption(PERSISTENT_DEFINITION)
        window = data["persistent_window"]
        if window:
            st.caption(f"当前观察窗口：{window[0]} → {window[1]}；按窗口净变化排序，展示全部符合条件的机构。")
        left, right = st.columns(2)
        for column, key, label in ((left, "persistent_increases", "持续增持"), (right, "persistent_decreases", "持续减持")):
            with column:
                st.markdown(f"**{label}**")
                frame = data[key]
                if frame.empty:
                    st.caption("工作日快照不足 4 个，或没有符合当前趋势口径的 Participant。")
                else:
                    show_table(frame)


def show_participant_tracking(frames):
    st.subheader("单个机构 · 上市以来持仓趋势")
    st.caption("机构指 CCASS 参与者，包括券商、银行及托管机构等，不代表最终实益拥有人。")
    participants = pd.concat(list(frames.values())).drop_duplicates("participant_id", keep="last").set_index("participant_id")
    ids = sorted(participants.index)
    pid = st.selectbox("选择 Participant", ids, format_func=lambda value: f"{value} · {participants.loc[value, 'participant_name']}", key="trend_participant")
    history = []
    for day, frame in frames.items():
        match = frame[frame.participant_id == pid]
        history.append({"日期": pd.Timestamp(day), "持股数量（股）": int(match.shares.iloc[0]) if not match.empty else 0,
                        "占比（%）": float(match.percentage.iloc[0]) if not match.empty else 0.0, "该日存在记录": not match.empty})
    history = pd.DataFrame(history)
    st.line_chart(history, x="日期", y="持股数量（股）", color="#486888")
    st.caption("缺席日期按零处理；该曲线反映结算后持仓，不是实时成交。")
    with st.expander("查看逐日持仓明细"):
        st.dataframe(history, hide_index=True, width="stretch")


def show_custom_comparison(dates, frames):
    st.markdown("**对比对象：06731 在两个日期快照中各 Participant 的结算后持仓。每行一个 Participant。**")
    st.caption("持股变化 = 结束持股 − 起始持股；占比变化 = 结束占比 − 起始占比，单位为百分点。仅出现于一个日期的机构，另一日按 0 处理。")
    with st.form("comparison_form"):
        st.markdown("#### 1 · 设置对比参数")
        left, middle, right = st.columns(3)
        start = left.selectbox("开始日期（基准快照）", dates, index=0, key="compare_start")
        end = middle.selectbox("结束日期（目标快照）", dates, index=len(dates) - 1, key="compare_end")
        direction = right.selectbox("持股变化方向", ["全部", "增加", "减少", "不变"], key="compare_direction")
        left, middle, right = st.columns(3)
        keyword = left.text_input("Participant ID / 名称", placeholder="留空查询全部机构", key="compare_keyword")
        sort_by = middle.selectbox("排序方式", ["持股变化绝对值：从大到小", "持股变化：从大到小", "持股变化：从小到大",
                                                "占比变化：从大到小", "占比变化：从小到大", "结束持股：从大到小"], key="compare_sort")
        limit = right.selectbox("展示数量", ["全部", "Top 10", "Top 20", "Top 50"], key="compare_limit")
        submitted = st.form_submit_button("生成对比结果", type="primary", width="stretch")
    if submitted:
        if start >= end:
            st.session_state.pop("comparison_request", None)
            st.error("开始日期必须早于结束日期，请重新选择后生成结果。")
            return
        st.session_state.comparison_request = dict(start=start, end=end, direction=direction,
                                                   keyword=keyword.strip(), sort_by=sort_by, limit=limit)
    request = st.session_state.get("comparison_request")
    if request is None:
        st.info("选择参数后点击“生成对比结果”，在下方查看统一对比表。")
        return
    if request["start"] not in frames or request["end"] not in frames:
        st.warning("上次选择的快照已不存在，请重新生成结果。")
        return
    comparison = compare_snapshots(frames[request["start"]], frames[request["end"]])
    comparison = add_change_ranks(comparison)
    filtered, matched_count = filter_comparison(comparison, request)
    st.markdown("#### 2 · 对比结果")
    st.write(f"**基准：{request['start']} → 目标：{request['end']}**")
    st.caption(f"已应用：方向 {request['direction']} · 机构 {request['keyword'] or '全部'} · {request['sort_by']} · {request['limit']}。修改参数后须再次点击生成；下表及导出均对应这组已应用参数。")
    st.caption(f"区间共 {len(comparison)} 家 Participant；筛选匹配 {matched_count} 家，当前展示 {len(filtered)} 家。Top N 在方向及机构筛选后，按所选排序截取。")
    st.caption("增持 / 减持排名分别按整个所选区间全部机构的增加 / 减少股数排序，筛选后不重新排名；并列采用 1、1、3 的排名方式。无对应方向变化显示 —。")
    if filtered.empty:
        st.info("没有符合当前筛选条件的 Participant，可放宽条件后重新生成。")
    show_table(filtered, include_address=True)
    st.download_button("下载当前结果 CSV", filtered.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"06731_ccass_changes_{request['start']}_{request['end']}.csv", mime="text/csv", disabled=filtered.empty)


def add_change_ranks(comparison):
    result = comparison.copy()
    result["increase_rank"] = result.shares_change.where(result.shares_change > 0).rank(method="min", ascending=False).astype("Int64")
    result["decrease_rank"] = result.shares_change.where(result.shares_change < 0).rank(method="min", ascending=True).astype("Int64")
    columns = [column for column in comparison.columns if column != "address"]
    trailing = ["increase_rank", "decrease_rank"]
    if "address" in result.columns:
        trailing.append("address")
    return result[columns + trailing]


def filter_comparison(comparison, parameters):
    """仅筛选和排序已有计算结果，不改变持仓对比口径。"""
    result = comparison.copy()
    direction = parameters["direction"]
    if direction == "增加":
        result = result[result.shares_change > 0]
    elif direction == "减少":
        result = result[result.shares_change < 0]
    elif direction == "不变":
        result = result[result.shares_change == 0]
    keyword = parameters["keyword"].strip()
    if keyword:
        mask = result.participant_id.str.contains(keyword, case=False, regex=False) | result.participant_name.str.contains(keyword, case=False, regex=False)
        result = result[mask]
    matched_count = len(result)
    sort_by = parameters["sort_by"]
    column = "percentage_change" if sort_by.startswith("占比") else "end_shares" if sort_by.startswith("结束") else "shares_change"
    if "绝对值" in sort_by:
        result = result.assign(_magnitude=result.shares_change.abs()).sort_values(["_magnitude", "participant_id"], ascending=[False, True]).drop(columns="_magnitude")
    else:
        result = result.sort_values([column, "participant_id"], ascending=["从小到大" in sort_by, True])
    if parameters["limit"] != "全部":
        result = result.head(int(parameters["limit"].split()[-1]))
    return result.reset_index(drop=True), matched_count


def show_registry():
    st.info("待接入 · 尚未接入查册记录或完成查册校验。")
    st.caption("后续可对照指定日期的查册材料与 CCASS 快照；当前不推断 Participant 背后的最终实益拥有人。")
