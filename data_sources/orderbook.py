"""盘口和经纪队列；经纪队列不是券商成交记录。"""


def get_order_book(client, code, num=10, **kwargs):
    from futu import SubType
    client.subscribe([code], SubType.ORDER_BOOK)
    return client.call("get_order_book", code, num=num, **kwargs)


def get_broker_queue(client, code):
    """原样返回 (ret, bid_frame_table, ask_frame_table)。"""
    from futu import SubType
    client.subscribe([code], SubType.BROKER)
    return client.call("get_broker_queue", code)
