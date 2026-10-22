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
    from agent import run_agent, is_llm_configured
    from views.ui import apply_styles, render_notice
    from auto_ccass import render_auto_update_status
    from views.navigation import PARTICIPANT_MENU

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
    page = st.session_state.page
    apply_styles(assistant=page == "💬 AI 对话助手")
    with st.container(key="top_navigation"):
        columns = st.columns([1.4, 1, 1, 1, 1, 6], gap="small", vertical_alignment="center")
        with columns[0]:
            st.html('<div class="cc-nav-logo"><span>◈</span><strong>06731</strong></div>')
        for column, label, target, key in (
            (columns[1], "主看板", "📊 CCASS Dashboard", "nav_dashboard"),
            (columns[3], "多参与者对比", "区间对比", "nav_comparison"),
            (columns[4], "AI助手（待修改）", "💬 AI 对话助手", "nav_ai_top"),
        ):
            column.button(label, key=key, width="stretch", type="primary" if page == target else "secondary",
                          on_click=change_page, args=(target,))
        with columns[2]:
            with st.popover("持仓与交易", key="nav_participant", width="stretch",
                            type="primary" if page == "Participant 追踪" else "secondary"):
                for label, route, key in PARTICIPANT_MENU:
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
        llm_status = "智谱 GLM 已配置" if is_llm_configured() else "LLM 尚未配置"
        st.html('''<div class="cc-hero">
        <p>通过自然语言查询 06731 上市后的 CCASS 持仓变化</p>
        <span class="cc-badge">框架已就绪 · STATUS</span></div>'''.replace("STATUS", llm_status))
        render_notice()
        snapshot_dates = list(discover_snapshots())
        latest_label = f"{snapshot_dates[-1].month} 月 {snapshot_dates[-1].day} 日" if snapshot_dates else "最新数据日期"
        questions = ["6731 上市以来筹码主要流向哪里？", "最近哪个 Participant 增持最多？", "谁在持续减持？",
                     f"帮我总结 9 月 29 日到 {latest_label}的主要持仓变化。", "B01228 的持仓趋势怎么样？"]
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

        submitted = st.chat_input("询问持仓变化、Participant 趋势…", key="assistant_input")
        question = selected or typed or submitted
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
