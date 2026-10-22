"""主看板 CCASS 持仓变动表，复用本地快照和既有比较口径。"""
import pandas as pd
import streamlit as st

from analysis import compare_snapshots, get_monitoring_data
from participant_names import chinese_name


def make_change_table(comparison, direction="全部", keyword="", sort="股数增加最多"):
    frame = comparison.copy()
    frame["参与者名称"] = [chinese_name(row.participant_id, row.participant_name) or row.participant_name
                        for row in frame.itertuples()]
    if direction == "增加":
        frame = frame[frame.shares_change > 0]
    elif direction == "减少":
        frame = frame[frame.shares_change < 0]
    elif direction == "不变":
        frame = frame[frame.shares_change == 0]
    if keyword.strip():
        mask = pd.Series(False, index=frame.index)
        for column in ("参与者名称", "participant_id", "participant_name"):
            mask |= frame[column].str.contains(keyword.strip(), case=False, regex=False, na=False)
        frame = frame[mask]
    column, ascending = {
        "股数增加最多": ("shares_change", False),
        "股数减少最多": ("shares_change", True),
        "最新持股最多": ("end_shares", False),
        "占比增加最多": ("percentage_change", False),
    }[sort]
    frame = frame.sort_values([column, "participant_id"], ascending=[ascending, True]).reset_index(drop=True)
    frame = frame.rename(columns={"participant_id": "参与者编号", "start_shares": "变动前股数",
        "start_percentage": "变动前占比（%）", "shares_change": "变动股数",
        "percentage_change": "占比变动（百分点）", "end_shares": "最新持股量", "end_percentage": "最新占比（%）"})
    frame.insert(0, "序号", range(1, len(frame) + 1))
    return frame[["序号", "参与者名称", "参与者编号", "变动前股数", "变动前占比（%）", "变动股数",
                  "占比变动（百分点）", "最新持股量", "最新占比（%）"]]


def change_color(value):
    return "color: #d64b50" if value > 0 else "color: #25845e" if value < 0 else "color: #25282c"


def render_ccass_overview():
    with st.container(key="ccass_change_overview"):
        st.subheader("CCASS 持仓变动")
        try:
            data = get_monitoring_data()
        except (ValueError, OSError, OverflowError) as exc:
            st.error(f"本地持仓数据读取失败：{exc}")
            return
        dates, frames = data["dates"], data["frames"]
        if len(dates) < 2:
            st.info("至少需要两个日期的真实 CCASS 快照，才能展示变动表。")
            return
        mode_column, date_column = st.columns([1.4, 2], vertical_alignment="center")
        with mode_column:
            mode = st.segmented_control("比较范围", ["相邻快照", "上市以来", "自选区间"],
                default="相邻快照", key="ccass_home_period", label_visibility="collapsed") or "相邻快照"
        with date_column:
            if mode == "自选区间":
                first, second = st.columns(2)
                start = first.selectbox("基准日期", dates[:-1], index=len(dates) - 2, key="ccass_home_start")
                available_ends = [day for day in dates if day > start]
                end = second.selectbox("目标日期", available_ends, index=len(available_ends) - 1, key="ccass_home_end")
            else:
                start, end = (dates[-2], dates[-1]) if mode == "相邻快照" else (dates[0], dates[-1])
                st.caption(f"基准快照 {start} → 目标快照 {end}")
        if mode == "上市以来" and str(start) != "2026-09-29":
            st.caption(f"上市日快照缺失，当前以最早已有快照 {start} 为基准。")
        filters = st.columns([1, 1.7, 1.3], vertical_alignment="bottom")
        direction = filters[0].selectbox("持仓方向", ["全部", "增加", "减少", "不变"], key="ccass_home_direction")
        keyword = filters[1].text_input("搜索参与者", placeholder="中文、英文或参与者编号", key="ccass_home_search")
        sort = filters[2].selectbox("排序", ["股数增加最多", "股数减少最多", "最新持股最多", "占比增加最多"], key="ccass_home_sort")
        comparison = compare_snapshots(frames[start], frames[end])
        if comparison.shares_change.eq(0).all() and comparison.percentage_change.eq(0).all():
            st.caption(f"{start} 与 {end} 两份快照的参与者持仓及占比相同，本区间变动均为 0；可切换自选区间查看其他日期。")
        table = make_change_table(comparison, direction, keyword, sort)
        st.caption(f"{len(table)} / {len(comparison)} 家参与者 · 红色增加，绿色减少 · 序号按当前排序生成；点击列标题可重新排序。")
        if table.empty:
            st.caption("没有符合当前筛选条件的参与者。")
        formats = {"变动前股数": "{:,.0f}", "变动股数": "{:+,.0f}", "最新持股量": "{:,.0f}",
                   "变动前占比（%）": "{:.2f}%", "最新占比（%）": "{:.2f}%", "占比变动（百分点）": "{:+.4f}"}
        styled = table.style.set_properties(**{"background-color": "#fff", "color": "#25282c"}).format(formats)
        styled = styled.map(change_color, subset=["变动股数", "占比变动（百分点）"])
        st.dataframe(styled, hide_index=True, width="stretch", height=430,
                     column_config={"参与者名称": st.column_config.TextColumn(width="large")})
        st.download_button("下载当前变动表", table.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"06731_ccass_changes_{start}_{end}.csv", mime="text/csv", disabled=table.empty)
        st.caption("比较的是上述两份实际快照，未必是相邻交易日；缺席参与者按既有口径以零计。持仓变化不等于券商净买卖或资金流向。")
