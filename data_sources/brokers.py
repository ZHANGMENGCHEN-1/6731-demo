"""十大券商净买卖：保留 days_before 原始交易日偏移语义。"""


def get_top_ten_buy_sell_brokers(client, code, days_before=0):
    """0=当日；正整数=前第 N 个交易日；不转换日期，不补全未上榜券商。"""
    return client.call("get_top_ten_buy_sell_brokers", code, days_before=days_before)
