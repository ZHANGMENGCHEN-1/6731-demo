"""多个 CCASS 参与者在同一日期范围内的原始持仓对照。"""
import altair as alt
import pandas as pd
import streamlit as st

from analysis import get_monitoring_data
from participant_names import chinese_name


def comparison_data(frames, selected, start, end):
    days = sorted(day for day in frames if start <= day <= end)
    records, summary = [], []
    for pid in selected:
        known = [f.loc[f.participant_id == pid].iloc[0] for day, f in sorted(frames.items())
                 if not f.loc[f.participant_id == pid].empty and day <= end]
        original_name = str(known[-1].participant_name) if known else pid
        name = chinese_name(pid, original_name) or original_name
        own = []
        for day in days:
            match = frames[day].loc[frames[day].participant_id == pid]
            record = {"date": str(day), "participant_id": pid, "participant_name": original_name,
                      "participant_name_zh": chinese_name(pid, original_name),
                      "shares": int(match.iloc[0].shares) if not match.empty else None,
                      "percentage": float(match.iloc[0].percentage) if not match.empty else None,
                      "record_exists": not match.empty, "label": f"{pid} · {name}"}
            records.append(record)
            own.append(record)
        first, last = own[0], own[-1]
        summary.append({"参与者编号": pid, "参与者名称": name,
                        "期初持股（股）": first["shares"], "期末持股（股）": last["shares"],
                        "持股变化（股）": last["shares"] - first["shares"] if first["record_exists"] and last["record_exists"] else None,
                        "期初占比（%）": first["percentage"], "期末占比（%）": last["percentage"],
                        "占比变化（百分点）": last["percentage"] - first["percentage"] if first["record_exists"] and last["record_exists"] else None})
    return pd.DataFrame(records), pd.DataFrame(summary)


def relative_history(history):
    """以所选区间首日为基准；首日缺席时不改用后续日期，也不补零。"""
    result = history.copy()
    baseline = result.sort_values("date").drop_duplicates("participant_id", keep="first").set_index("participant_id")
    result["shares_change"] = result.shares - result.participant_id.map(baseline.shares)
    result["percentage_change"] = result.percentage - result.participant_id.map(baseline.percentage)
    return result


def render_participant_comparison():
    with st.container(key="multi_participant_workspace"):
        st.subheader("多参与者对比")
        st.caption("选择多家 CCASS 参与者，对比相对期初的持股变化；下方表格保留实际持仓。")
        try:
            data = get_monitoring_data()
        except (ValueError, OSError, OverflowError) as exc:
            st.error(f"本地持仓数据读取失败：{exc}")
            return
        dates, frames = data["dates"], data["frames"]
        if len(dates) < 2:
            st.caption("至少需要两个日期的 CCASS 快照。")
            return
        first, last = st.columns(2)
        start = first.selectbox("开始日期", dates[:-1], key="multi_start")
        ends = [day for day in dates if day > start]
        end = last.selectbox("结束日期", ends, index=len(ends) - 1, key="multi_end")
        in_range = [frames[day] for day in dates if start <= day <= end]
        names = pd.concat(in_range).drop_duplicates("participant_id", keep="last").set_index("participant_id")
        ids = sorted(names.index)
        defaults = frames[end].sort_values("shares", ascending=False).participant_id.head(3).tolist()
        selected = st.multiselect("选择参与者（最多 8 家）", ids, default=defaults,
            format_func=lambda pid: f"{pid} · {chinese_name(pid, names.loc[pid, 'participant_name']) or names.loc[pid, 'participant_name']}",
            max_selections=8, key="multi_participants")
        if not selected:
            st.caption("请选择至少一家参与者。")
            return
        history, summary = comparison_data(frames, selected, start, end)
        choices = ["股数变化", "占比变化"]
        if st.session_state.get("multi_measure") not in (None, *choices):
            del st.session_state["multi_measure"]
        measure = st.segmented_control("曲线指标", choices, default=choices[0], key="multi_measure") or choices[0]
        field, unit = ("shares_change", "较期初股数变化（股）") if measure == "股数变化" else ("percentage_change", "较期初占比变化（百分点）")
        changes = relative_history(history)
        chart = alt.Chart(changes).mark_line(invalid="break-paths-show-domains").encode(
            x=alt.X("date:T", title="快照日期"),
            y=alt.Y(f"{field}:Q", title=unit, scale=alt.Scale(zero=True)),
            color=alt.Color("label:N", title="参与者", legend=alt.Legend(orient="bottom", labelLimit=450)),
            tooltip=[alt.Tooltip("date:T", title="日期", format="%Y-%m-%d"),
                     alt.Tooltip("label:N", title="参与者"),
                     alt.Tooltip("shares_change:Q", title="较期初股数变化", format="+,.0f"),
                     alt.Tooltip("percentage_change:Q", title="较期初占比变化（百分点）", format="+.4f"),
                     alt.Tooltip("shares:Q", title="持股数量", format=","),
                     alt.Tooltip("percentage:Q", title="占比（%）", format=".2f")],
        ).properties(height=330).interactive()
        chart = chart.properties(background="#fff").configure_view(fill="#fff", stroke="#d3dae2")
        st.altair_chart(chart, width="stretch", theme=None)
        st.caption(f"以 {start} 为共同基准，0 表示较期初无变化；正数增加、负数减少。期初缺席的参与者不计算变化曲线。")
        st.caption(f"{start} → {end} · {len(selected)} 家参与者 · {len(in_range)} 份实际快照；支持缩放与拖动。缺席记录保留为空，不补零；缺失日期不补造快照。")
        st.subheader("期初与期末持仓")
        formats = {column: "{:+,.0f}" if column == "持股变化（股）" else "{:,.0f}" for column in summary if "（股）" in column}
        formats.update({column: "{:.4f}" for column in summary if "占比" in column})
        st.dataframe(summary.style.set_properties(**{"background-color": "#fff", "color": "#171717"}).format(formats, na_rep="—"),
                     hide_index=True, width="stretch")
        st.caption("占比变化以百分点计；期初或期末无记录时不推算变化。CCASS 参与者是结算／托管渠道，不代表最终实益拥有人。")
        with st.expander("逐日持仓数据"):
            st.dataframe(history.drop(columns="label").style.set_properties(**{"background-color": "#fff", "color": "#171717"}),
                         hide_index=True, width="stretch")
        st.download_button("下载所选参与者逐日 CSV", history.drop(columns="label").to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"06731_participants_{start}_{end}.csv", mime="text/csv")
