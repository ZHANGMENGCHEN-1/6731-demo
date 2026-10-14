"""启动：python -m streamlit run app.py"""
import streamlit as st
import importlib
import inspect
import agent
from analysis import discover_snapshots, load_snapshot, compare_snapshots, top_changes, make_summary

# 热更新 app.py 时，长时间运行的 Streamlit 进程可能仍缓存旧版 agent。
# 仅在检测到旧函数签名时重载，正常 rerun 不重复重载模块。
if "on_text" not in inspect.signature(agent.run_agent).parameters:
    importlib.invalidate_caches()
    importlib.reload(agent)
from agent import run_agent, is_llm_configured
from ui import apply_styles, render_notice

st.set_page_config(page_title="06731 · CCASS Research", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
if "page" not in st.session_state:
    st.session_state.page = "💬 AI 分析助手"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_runs" not in st.session_state:
    st.session_state.agent_runs = []


def change_page(page):
    st.session_state.page = page


def clear_chat():
    st.session_state.messages = []
    st.session_state.agent_runs = []


page = st.session_state.page
apply_styles(assistant=page == "💬 AI 分析助手")
with st.sidebar:
    st.html('<div class="cc-brand"><div class="cc-brand-icon">◈</div><div><strong>CCASS Research</strong><small>06731 · WORKSPACE</small></div></div>')
    st.html('<div class="cc-section">工作空间</div>')
    for label, key, icon in (("AI 分析助手", "nav_assistant", ":material/chat_bubble_outline:"),
                             ("CCASS Dashboard", "nav_dashboard", ":material/bar_chart:")):
        target = "💬 AI 分析助手" if key == "nav_assistant" else "📊 CCASS Dashboard"
        st.button(label, key=key, icon=icon, width="stretch", type="primary" if page == target else "secondary",
                  on_click=change_page, args=(target,))
    st.divider()
    dates_available = list(discover_snapshots())
    latest = str(dates_available[-1]) if dates_available else "暂无数据"
    data_status = "本地数据已就绪" if dates_available else "等待本地数据"
    st.html(f'<div class="cc-status"><strong>● {data_status}</strong><p>最新快照 · {latest}</p><p>{len(dates_available)} 个日期 · 06731</p></div>')
    if page == "💬 AI 分析助手":
        st.button("清空对话", key="clear_chat", icon=":material/delete_outline:", width="stretch", on_click=clear_chat)
    with st.expander("开发设置"):
        debug = st.checkbox("显示 Agent Debug", value=False, key="agent_debug")
        st.caption("智谱已配置 · Python 数据工具 + LLM 解读" if is_llm_configured() else "LLM 尚未配置 · 当前仅执行本地 Python 工具")
    st.caption("CCASS 持仓观察 · 内部研究 Demo")


def render_assistant(typed=None):
    llm_status = "智谱 GLM 已配置" if is_llm_configured() else "LLM 尚未配置"
    st.html('''<div class="cc-hero">
    <h1>06731 CCASS AI 分析助手</h1>
    <p>通过自然语言查询 06731 上市后的 CCASS 持仓变化</p>
    <span class="cc-badge">框架已就绪 · STATUS</span></div>'''.replace("STATUS", llm_status))
    render_notice()
    questions = ["6731 上市以来筹码主要流向哪里？", "最近哪个 Participant 增持最多？", "谁在持续减持？",
                 "帮我总结 9 月 29 日到 10 月 13 日的主要持仓变化。", "B01228 的持仓趋势怎么样？"]
    selected = None
    with st.expander("从一个问题开始" if not st.session_state.messages else "推荐问题", expanded=not st.session_state.messages):
        st.html('<div class="cc-helper">选择一个问题，或在下方输入你想了解的内容</div>')
        for index, question in enumerate(questions):
            if st.button(question, key=f"suggestion_{index}", width="stretch"):
                selected = question
    question = selected or typed
    assistant_index = 0
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=None if message["role"] == "user" else ":material/auto_awesome:"):
            st.write(message["content"])
            if message["role"] == "assistant":
                result = st.session_state.agent_runs[assistant_index]
                context = result["context"]
                if context.error:
                    st.warning(f"本地工具未完成：{context.error}")
                if debug:
                    with st.expander("Agent Debug"):
                        st.write("用户问题：", context.question)
                        st.caption(context.routing_note)
                        st.write("候选工具：", context.candidate_tool)
                        st.json({"participant_id": context.participant_id, "date_range": context.date_range,
                                 "arguments": context.tool_arguments, "dataset_info": context.dataset_info})
                        st.write("工具执行结果（真实 Python 数据，非 LLM 回答）：")
                        if context.error:
                            st.error(context.error)
                        elif hasattr(context.tool_result, "columns"):
                            st.dataframe(context.tool_result, hide_index=True, width="stretch")
                            if context.tool_result.empty:
                                st.caption("结果为空：没有符合当前工具定义的 Participant。")
                        else:
                            st.json(context.tool_result)
                        status = "已请求智谱" if result.get("llm_called") else "未调用 LLM"
                        st.caption(f"已构造 {len(result['llm_messages'])} 条消息 · {status}")
                assistant_index += 1

    if question and question.strip():
        history = [dict(message) for message in st.session_state.messages]
        st.session_state.messages.append({"role": "user", "content": question.strip()})
        with st.chat_message("user"):
            st.write(question.strip())
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            answer = st.empty()
            answer.caption("正在准备数据，等待模型回复…")
            result = run_agent(question, history, on_text=lambda text: answer.markdown(text + " ▍"))
            # 完成后移除光标；若响应中断，使用明确错误替换未完成的正文。
            answer.markdown(result["response"])
        st.session_state.agent_runs.append(result)
        st.session_state.messages.append({"role": "assistant", "content": result["response"]})
        st.rerun()


if page == "💬 AI 分析助手":
    # 必须在主页面根级调用；嵌入 container 会变成普通流式布局，无法固定在屏幕底部。
    typed = st.chat_input("询问持仓变化、Participant 趋势…", key="assistant_input")
    render_assistant(typed)
    st.stop()

st.html('''<div class="cc-hero"><div class="cc-eyebrow">HOLDINGS OVERVIEW / 06731</div>
<h1>06731 上市后 CCASS 持仓变化监控</h1>
<p>对比不同日期的结算后持仓，观察 Participant 层面的分布变化。</p></div>''')
st.caption("内部 Demo · HKEX CCASS 每日快照 · 本地 CSV")
render_notice()
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
