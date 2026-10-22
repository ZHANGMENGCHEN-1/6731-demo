# 页面与路由

- `application.py`：页面装配、顶部导航、侧边栏和 AI 助手。
- `navigation.py`：菜单名称与稳定路由标识。
- `dashboard.py`：根据路由分发页面、参与者持仓追踪。
- `market_home.py`：主看板。
- `ccass_overview.py`：CCASS 持仓变动。
- `broker_history.py`：券商历史净买卖。
- `trade_ticker.py`：最近逐笔成交。
- `participant_comparison.py`：多参与者对比。
- `ui.py`：共享样式。

从项目根目录执行 `python -m streamlit run app.py`。采集和同步命令仍从根目录运行。
使用 `views` 而非 Streamlit 自动发现的 `pages` 目录，以保持现有自定义菜单。
