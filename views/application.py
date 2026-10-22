"""Streamlit ??????????"""

def render_app():
    """启动：python -m streamlit run app.py"""
    import streamlit as st
    import importlib
    import inspect
    import agent
    from analysis import discover_snapshots

    # 热更新 app.py 时，长时间运行的 Streamlit 进程可能仍缓存旧版 agent。
    # 仅在检测到旧函数签名时重载，正常 rerun 不重复重载模块。
    if "on_text" not in inspect.signature(agent.run_agent).parameters:
        importlib.invalidate_caches()
        importlib.reload(agent)
    from agent import run_agent, is_llm_configured, _serializable
    from views.ui import apply_styles, render_notice
    from auto_ccass import render_auto_update_status
    from views.navigation import CCASS_MENU, MARKET_MENU

    st.set_page_config(page_title="06731 市场与持仓看板", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
    if "page" not in st.session_state:
        st.session_state.page = "📊 CCASS Dashboard"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_runs" not in st.session_state:
        st.session_state.agent_runs = []


    def change_page(page):
        st.session_state.page = page


    def open_participant_section(section):
        st.session_state.page = "Participant 追踪"
        st.session_state.participant_workspace_view = section


    def clear_chat():
        st.session_state.messages = []
        st.session_state.agent_runs = []


    if st.session_state.page == "查册校验":
        st.session_state.page = "📊 CCASS Dashboard"
    if st.session_state.page == "区间对比":
        open_participant_section("participant_comparison")
    page = st.session_state.page
    apply_styles(assistant=page == "💬 AI 对话助手")
    with st.container(key="top_navigation"):
        columns = st.columns([2.1, 1, 1, 1, 1, 5.3], gap="small", vertical_alignment="center")
        with columns[0]:
            st.html('<div class="cc-nav-logo"><span>◈</span><strong>06731 本末科技</strong></div>')
        for column, label, target, key in (
            (columns[1], "主看版", "📊 CCASS Dashboard", "nav_dashboard"),
            (columns[4], "AI助手", "💬 AI 对话助手", "nav_ai_top"),
        ):
            column.button(label, key=key, width="stretch", type="primary" if page == target else "secondary",
                          on_click=change_page, args=(target,))
        section = st.session_state.get("participant_workspace_view", "ccass_changes")
        for column, title, menu, menu_key in (
            (columns[2], "CCASS 持仓", CCASS_MENU, "nav_ccass"),
            (columns[3], "市场交易", MARKET_MENU, "nav_market"),
        ):
            active = page == "Participant 追踪" and section in {route for _, route, _ in menu}
            with column:
                with st.popover(title, key=menu_key, width="stretch",
                                type="primary" if active else "secondary"):
                    for label, route, key in menu:
                        st.button(label, key=key, width="stretch", on_click=open_participant_section, args=(route,))
    with st.sidebar:
        st.html('<div class="cc-brand"><div class="cc-brand-icon">◈</div><div><strong>CCASS</strong><small>06731 · WORKSPACE</small></div></div>')
        st.html('<div class="cc-section">AI工具</div>')
        st.button("AI 对话助手", key="nav_assistant", icon=":material/chat_bubble_outline:", width="stretch",
                  type="primary" if page == "💬 AI 对话助手" else "secondary",
                  on_click=change_page, args=("💬 AI 对话助手",))
        st.divider()
        dates_available = list(discover_snapshots())
        latest = str(dates_available[-1]) if dates_available else "暂无数据"
        data_status = "本地数据已就绪" if dates_available else "等待本地数据"
        st.html(f'<div class="cc-status"><strong>● {data_status}</strong><p>最新快照 · {latest}</p><p>{len(dates_available)} 个日期 · 06731</p></div>')
        if page == "💬 AI 对话助手":
            st.button("清空对话", key="clear_chat", icon=":material/delete_outline:", width="stretch", on_click=clear_chat)
        with st.expander("开发设置"):
            debug = st.checkbox("显示 Agent Debug", value=False, key="agent_debug")
            st.caption("智谱已配置 · Python 数据工具 + LLM 解读" if is_llm_configured() else "LLM 尚未配置 · 当前仅执行本地 Python 工具")
        st.caption("CCASS 持仓观察 · 内部研究 Demo")
        render_auto_update_status()


    def render_assistant(typed=None):
        # 像素高度启用 Streamlit 原生滚动跟随；实际高度由 CSS 按视口剩余空间撑满。
        messages = st.container(height=480, border=False, key="assistant_messages", autoscroll=True)
        with messages:
            llm_status = "智谱 GLM 已配置" if is_llm_configured() else "LLM 尚未配置"
            st.html('''<div class="cc-hero">
            <p>通过自然语言查询 06731 的持仓、行情和市场交易</p>
            <span class="cc-badge">STATUS</span></div>'''.replace("STATUS", llm_status))
            st.caption("支持 CCASS 持仓变动、参与者对比、行情与分时、券商净买卖、最近逐笔排名；日期和可用范围以查询数据为准。")
            questions = ["06731 最近可用的股价、涨跌幅和成交额是多少？",
                         "今天净买入和净卖出最多的前5家券商分别是谁？",
                         "昨天的券商净买卖情况怎么样？",
                         "按成交金额列出最近逐笔成交 Top 20。",
                         "最近两个快照哪些参与者增持最多？",
                         "比较 B01228 和 B01955 上市以来的持仓变化。"]
            selected = None
            with st.expander("从一个问题开始" if not st.session_state.messages else "推荐问题", expanded=not st.session_state.messages):
                st.html('<div class="cc-helper">选择一个问题，或在下方输入你想了解的内容</div>')
                for index, question in enumerate(questions):
                    if st.button(question, key=f"suggestion_{index}", width="stretch"):
                        selected = question
            assistant_index = 0
            for message in st.session_state.messages:
                with st.chat_message(message["role"], avatar=None if message["role"] == "user" else ":material/auto_awesome:"):
                    st.write(message["content"])
                    if message["role"] == "assistant":
                        result = st.session_state.agent_runs[assistant_index]
                        context = result["context"]
                        if context.error:
                            st.warning(f"本地工具未完成：{context.error}")
                        if context.tool_result is not None:
                            with st.expander("查看本次查询数据", key=f"assistant_evidence_{assistant_index}"):
                                evidence_rows = context.tool_result if isinstance(context.tool_result, list) else [{
                                    "tool": context.candidate_tool, "result": context.tool_result, "error": context.error}]
                                for evidence in evidence_rows:
                                    st.caption(evidence["tool"])
                                    if evidence["error"]:
                                        st.warning(evidence["error"])
                                        continue
                                    value = evidence["result"]
                                    if hasattr(value, "columns"):
                                        st.dataframe(value, hide_index=True, width="stretch")
                                    elif isinstance(value, dict):
                                        st.json(_serializable({k: v for k, v in value.items() if not hasattr(v, "columns")}))
                                        for name, table in value.items():
                                            if hasattr(table, "columns"):
                                                st.caption(name)
                                                st.dataframe(table, hide_index=True, width="stretch")
                                    else:
                                        st.json(_serializable(value))
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
                                    st.json(_serializable(context.tool_result))
                                status = "已请求智谱" if result.get("llm_called") else "未调用 LLM"
                                st.caption(f"已构造 {len(result['llm_messages'])} 条消息 · {status}")
                        assistant_index += 1

        with st.container(key="assistant_composer"):
            submitted = st.chat_input("查询持仓、行情、券商净买卖、逐笔成交…", key="assistant_input")
        question = selected or typed or submitted
        if question and question.strip():
            history = [dict(message) for message in st.session_state.messages]
            st.session_state.messages.append({"role": "user", "content": question.strip()})
            with messages:
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


    if page == "💬 AI 对话助手":
        with st.container(key="assistant_section"):
            with st.container(key="assistant_content"):
                render_assistant()
        st.stop()

    from views import dashboard
    # 热更新 app.py 后，进程可能仍持有旧版无参数 dashboard 函数。
    if "view" not in inspect.signature(dashboard.render_dashboard).parameters:
        importlib.invalidate_caches()
        importlib.reload(dashboard)

    dashboard.render_dashboard(view="主看板" if page == "📊 CCASS Dashboard" else page)
