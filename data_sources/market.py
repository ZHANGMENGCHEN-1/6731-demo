"""行情：原始快照、报价、K 线、分时和逐笔。"""


def get_market_snapshot(client, codes):
    codes = [codes] if isinstance(codes, str) else list(codes)
    return client.call("get_market_snapshot", codes)


def get_stock_quote(client, codes):
    from futu import SubType
    codes = [codes] if isinstance(codes, str) else list(codes)
    client.subscribe(codes, SubType.QUOTE)
    return client.call("get_stock_quote", codes)


def request_history_kline(client, code, start=None, end=None, **kwargs):
    """保留 SDK 的 ktype/autype/max_count/page_req_key 等参数及三元组返回值。"""
    return client.call("request_history_kline", code, start=start, end=end, **kwargs)


def get_rt_data(client, code):
    from futu import SubType
    client.subscribe([code], SubType.RT_DATA)
    return client.call("get_rt_data", code)


def get_rt_ticker(client, code, num=500):
    from futu import SubType
    client.subscribe([code], SubType.TICKER)
    return client.call("get_rt_ticker", code, num=num)
