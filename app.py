"""启动：python -m streamlit run app.py"""
import streamlit as st
from analysis import discover_snapshots, load_snapshot, compare_snapshots, top_changes, make_summary

st.set_page_config(page_title="06731 上市后 CCASS 持仓变化监控", page_icon="📊", layout="wide")
st.html("""
<header style="background:#152b46; padding:24px 28px; border-radius:10px; margin-bottom:16px;">
    <h1 style="color:#ffffff; font-size:30px; line-height:1.4; margin:0; padding:0;">
        06731 上市后 CCASS 持仓变化监控
    </h1>
</header>
""")
st.caption("内部 Demo · HKEX CCASS 每日快照 · 本地 CSV")
st.warning("CCASS Participant 持仓反映的是券商、托管机构等参与者层面的结算后持仓，不等于最终实益拥有人，也不代表实时成交方向。本页面仅用于观察不同日期之间的持仓位置变化。")
snapshots = discover_snapshots()
dates = list(snapshots)
a, b, c, d = st.columns(4)
a.metric("股票代码", "06731")
b.metric("上市日期", "2026-09-29")
c.metric("当前数据最新日期", str(dates[-1]) if dates else "暂无")
d.metric("已获取数据日期数", len(dates))
st.caption("来源：香港交易所 CCASS Shareholding Search。数据最新日期按本地文件统计，并非实时查询；上市日期按项目指定。")
st.markdown("[查看 HKEX 查询页面](https://www3.hkexnews.hk/sdw/search/searchsdw.aspx)")
if len(dates) < 2:
    st.info("至少需要两个真实日期的 CSV。请先运行 python fetch_ccass.py 06731 2026-09-29 2026-10-13")
    st.stop()
left, right = st.columns(2)
start = left.selectbox("开始日期", dates, index=0)
end = right.selectbox("结束日期", dates, index=len(dates) - 1)
if start >= end:
    st.info("开始日期必须早于结束日期。")
    st.stop()
try:
    comparison = compare_snapshots(load_snapshot(snapshots[start]), load_snapshot(snapshots[end]))
except (ValueError, OSError, OverflowError) as exc:
    st.error(f"数据读取失败：{exc}")
    st.stop()
increases, decreases = top_changes(comparison)
st.subheader("主要持仓变化")
left, right = st.columns(2)
for column, frame, direction in ((left, increases, "增加"), (right, decreases, "减少")):
    with column:
        if frame.empty:
            st.metric(f"持仓{direction}股数", "0 股")
            st.caption(f"所选期间无持仓{direction}的 Participant。")
        else:
            row = frame.iloc[0]
            st.metric(f"持仓{direction}股数（最多）", f"{abs(int(row.shares_change)):,} 股")
            st.write(f"持仓{direction}最多的 Participant：**{row.participant_name}**（{row.participant_id}）")
st.subheader("规则总结")
st.info(make_summary(comparison, start, end))
st.caption("计算口径：结束持仓 − 起始持仓；占比变化单位为百分点。仅出现于一日的 Participant，另一日按 0 处理。股数和占比均直接读取 HKEX，未对占比重新归一化。")

LABELS = {"participant_id": "Participant ID", "participant_name": "Participant Name", "address": "地址",
          "start_shares": "起始持仓", "end_shares": "结束持仓", "shares_change": "持仓变化",
          "start_percentage": "起始占比（%）", "end_percentage": "结束占比（%）", "percentage_change": "占比变化（百分点）"}


def show_table(frame, include_address=False):
    if not include_address:
        frame = frame.drop(columns="address")
    st.dataframe(frame.rename(columns=LABELS).style.format({
        "起始持仓": "{:,.0f}", "结束持仓": "{:,.0f}", "持仓变化": "{:+,.0f}",
        "起始占比（%）": "{:.2f}", "结束占比（%）": "{:.2f}", "占比变化（百分点）": "{:+.2f}",
    }), hide_index=True, width="stretch")


for title, frame, color in (("持仓增加 Top 10", increases, "#167d9a"), ("持仓减少 Top 10", decreases, "#b95858")):
    st.subheader(title)
    if frame.empty:
        st.caption("所选期间没有符合条件的 Participant。")
    else:
        chart = frame.assign(label=frame.participant_id + " · " + frame.participant_name)
        st.bar_chart(chart, x="label", y="shares_change", color=color, x_label="Participant", y_label="持仓变化（股）")
        show_table(frame)
st.subheader("完整持仓变化对比")
show_table(comparison, include_address=True)
st.download_button("下载完整对比 CSV", comparison.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"06731_ccass_changes_{start}_{end}.csv", mime="text/csv")
st.caption("只读取 data/ccass_YYYY-MM-DD.csv，旧 sample_ccass 模拟文件不参与分析。非查询日期返回的前一日快照不另存为当天数据。")
