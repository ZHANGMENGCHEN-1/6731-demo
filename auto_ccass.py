"""页面打开时后台增量更新；同一服务进程共享任务并限制检查频率。"""
from datetime import datetime, timezone, timedelta
from threading import Lock, Thread
import time

import streamlit as st


class AutoCCASSUpdater:
    def __init__(self, interval=900, update=None):
        self.interval = interval
        self._update = update
        self._lock = Lock()
        self._last_start = None
        self._state = {"running": False, "finished_at": None, "error": None}

    def start_and_status(self):
        with self._lock:
            now = time.monotonic()
            if not self._state["running"] and (self._last_start is None or now - self._last_start >= self.interval):
                self._last_start = now
                self._state.update(running=True, error=None)
                Thread(target=self._run, daemon=True, name="ccass-auto-update").start()
            return dict(self._state)

    def _run(self):
        error = None
        try:
            if self._update is None:
                from fetch_latest import main
                code = main()
            else:
                code = self._update()
            if code != 0:
                error = "更新未完成，继续使用本地快照；详情见 logs/fetch_latest.log。"
        except Exception:
            error = "更新异常，继续使用本地快照；请检查网络和更新日志。"
        with self._lock:
            self._state.update(running=False, error=error,
                               finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat())


@st.cache_resource
def _updater():
    return AutoCCASSUpdater()


def start_auto_update():
    from cloud_store import uses_cloud, get_store
    if uses_cloud():
        try:
            dates = get_store().dates("ccass")
            return {"running": False, "finished_at": None, "error": None, "cloud": True,
                    "latest": str(dates[-1]) if dates else "暂无"}
        except ValueError:
            return {"running": False, "finished_at": None, "error": "云端 CCASS 暂不可用，请检查同步程序和数据库配置。", "cloud": True}
    return _updater().start_and_status()


@st.fragment(run_every=5)
def render_auto_update_status():
    state = start_auto_update()
    if state.get("cloud"):
        st.caption(state["error"] or f"CCASS 来自 Supabase · 最新持仓日 {state['latest']} · 本机采集端负责更新")
    elif state["running"]:
        st.caption("CCASS 正在后台检查并补充新快照…")
    elif state["error"]:
        st.caption(state["error"])
    else:
        st.caption("CCASS 已完成自动检查 · 每15分钟最多检查一次")
    finished = state["finished_at"]
    if finished and finished != st.session_state.get("ccass_update_seen"):
        st.session_state.ccass_update_seen = finished
        st.rerun()
