"""持仓监控首页与原有自定义日期比较；仅使用本地 Python 计算。"""
import pandas as pd
import streamlit as st
from analysis import get_monitoring_data, compare_snapshots, top_changes, make_summary, PERSISTENT_DEFINITION
from ui import render_notice

LABELS = {"participant_id": "Participant ID", "participant_name": "Participant Name", "address": "地址",
          "start_shares": "起始持仓", "end_shares": "结束持仓", "shares_change": "持仓变化",
          "start_percentage": "起始占比（%）", "end_percentage": "结束占比（%）", "percentage_change": "占比变化（百分点）",
          "direction_count": "同向区间数", "interval_count": "总区间数", "direction_share": "同向变化量占比（%）",
          "window_start": "窗口起日", "window_end": "窗口止日"}


def show_table(frame, include_address=False):
    if not include_address:
        frame = frame.drop(columns="address", errors="ignore")
    st.dataframe(frame.rename(columns=LABELS).style.format({
        "起始持仓": "{:,.0f}", "结束持仓": "{:,.0f}", "持仓变化": "{:+,.0f}",
        "起始占比（%）": "{:.2f}", "结束占比（%）": "{:.2f}", "占比变化（百分点）": "{:+.2f}",
        "同向变化量占比（%）": "{:.1f}",
    }), hide_index=True, width="stretch")


def show_rankings(comparison, n, prefix):
    increases, decreases = top_changes(comparison)
    left, right = st.columns(2)
    for column, direction, frame, color in ((left, "增持", increases.head(n), "#16766b"),
                                             (right, "减持", decreases.head(n), "#b95858")):
        with column:
            st.markdown(f"**{prefix} Top {n} {direction}**")
            if frame.empty:
                st.caption("没有符合条件的 Participant。")
                continue
            chart = frame.assign(label=frame.participant_id + " · " + frame.participant_name)
            st.bar_chart(chart, x="label", y="shares_change", color=color, x_label="Participant", y_label="持仓变化（股）")
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


def render_dashboard():
    st.title("06731 持仓监控看板")
    st.caption("CCASS HOLDINGS MONITOR · 本地快照 · 结算后持仓观察")
    try:
        data = get_monitoring_data()
    except (ValueError, OSError, OverflowError) as exc:
        st.error(f"数据读取失败：{exc}")
        return
    dates, frames, workdays = data["dates"], data["frames"], data["workdays"]
    a, b, c, d = st.columns(4)
    a.metric("股票代码", "06731")
    b.metric("上市日期", "2026-09-29")
    c.metric("最新数据日期", str(dates[-1]) if dates else "暂无")
    d.metric("已获取日期数", len(dates))
    render_notice()
    st.caption("最新交易日栏目使用最近两个已有周一至周五快照，不额外接入交易所日历；周末快照不作为交易日。上市以来从最早已有快照至最新快照计算。")
    st.markdown("[HKEX 原始查询页面](https://www3.hkexnews.hk/sdw/search/searchsdw.aspx) · 本页面不自动抓取或刷新数据")
    if not dates:
        st.info("暂无真实 CSV，请先运行 fetch_ccass.py。")
        show_registry()
        return
    if dates[0].isoformat() != "2026-09-29":
        st.warning(f"上市日快照缺失，上市以来栏目当前以 {dates[0]} 为基准，不代表完整上市以来变化。")
    st.subheader("核心持仓变化")
    if data["latest_comparison"] is not None:
        show_leaders(data["latest_comparison"], "最新交易日", f"{workdays[-2]} → {workdays[-1]}")
    else:
        st.info("至少需要两个已有工作日快照，才能计算最新交易日变化。")
    if data["listing_comparison"] is not None:
        show_leaders(data["listing_comparison"], "上市以来", f"{dates[0]} → {dates[-1]}")
    st.divider()
    st.subheader("最新交易日 · Top 5")
    if data["latest_comparison"] is not None:
        st.caption(f"{workdays[-2]} → {workdays[-1]}；按持股数量变化排序。")
        show_rankings(data["latest_comparison"], 5, "最新交易日")
    else:
        st.caption("数据不足，暂不展示排名。")
    st.subheader("上市以来 · Top 10")
    if data["listing_comparison"] is not None:
        st.caption(f"{dates[0]} → {dates[-1]}")
        show_rankings(data["listing_comparison"], 10, "上市以来")
    else:
        st.caption("至少需要两个快照。")
    st.divider()
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
    st.divider()
    st.subheader("单个 Participant · 上市以来持仓趋势")
    participants = pd.concat(list(frames.values())).drop_duplicates("participant_id", keep="last").set_index("participant_id")
    ids = sorted(participants.index)
    pid = st.selectbox("选择 Participant", ids, format_func=lambda value: f"{value} · {participants.loc[value, 'participant_name']}", key="trend_participant")
    history = []
    for day, frame in frames.items():
        match = frame[frame.participant_id == pid]
        history.append({"日期": pd.Timestamp(day), "持股数量（股）": int(match.shares.iloc[0]) if not match.empty else 0,
                        "占比（%）": float(match.percentage.iloc[0]) if not match.empty else 0.0, "该日存在记录": not match.empty})
    history = pd.DataFrame(history)
    st.line_chart(history, x="日期", y="持股数量（股）", color="#16766b")
    st.caption("缺席日期按零处理；该曲线反映结算后持仓，不是实时成交。")
    with st.expander("查看逐日持仓明细"):
        st.dataframe(history, hide_index=True, width="stretch")
    st.divider()
    st.subheader("自定义日期对比")
    if len(dates) >= 2:
        show_custom_comparison(dates, frames)
    else:
        st.info("至少需要两个真实日期。")
    show_registry()


def show_custom_comparison(dates, frames):
    left, right = st.columns(2)
    start = left.selectbox("开始日期", dates, index=0, key="compare_start")
    end = right.selectbox("结束日期", dates, index=len(dates) - 1, key="compare_end")
    if start >= end:
        st.info("开始日期必须早于结束日期。")
        return
    comparison = compare_snapshots(frames[start], frames[end])
    show_leaders(comparison, "所选区间主要变化", f"{start} → {end}")
    st.info(make_summary(comparison, start, end))
    st.caption("结束 − 起始；占比变化单位为百分点。仅出现于一日的 Participant，另一日按 0 处理。占比直接读取 HKEX，未重新归一化。")
    show_rankings(comparison, 10, "自定义区间")
    st.markdown("**完整持仓变化对比**")
    show_table(comparison, include_address=True)
    st.download_button("下载完整对比 CSV", comparison.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"06731_ccass_changes_{start}_{end}.csv", mime="text/csv")


def show_registry():
    st.divider()
    st.subheader("查册校验")
    st.info("预留区域 · 尚未接入查册记录或完成查册校验。")
    st.caption("后续可对照指定日期的查册材料与 CCASS 快照；当前不推断 Participant 背后的最终实益拥有人。")
