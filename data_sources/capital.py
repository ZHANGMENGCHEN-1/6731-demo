"""资金流向和资金分布；保留数据商原有统计口径。"""


def get_capital_flow(client, code, **kwargs):
    """支持原接口 period_type/start/end 参数。"""
    return client.call("get_capital_flow", code, **kwargs)


def get_capital_distribution(client, code):
    return client.call("get_capital_distribution", code)
