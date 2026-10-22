"""页面标题与内部路由分开，修改文案不影响跳转。"""
PARTICIPANT_MENU = (
    ("查询CCASS持仓变动", "ccass_changes", "nav_ccass_changes"),
    ("查询券商历史净买卖", "broker_history", "nav_broker_history"),
    ("查询最近逐笔成交", "recent_trades", "nav_trade_ticker"),
)
LEGACY_PARTICIPANT_ROUTES = {
    "查询CCASS持仓变动": "ccass_changes", "CCASS 持仓变动": "ccass_changes",
    "查询券商历史净买卖": "broker_history", "最近成交 Top 20": "recent_trades",
    "查询最近成交 Top 20": "recent_trades",
}
