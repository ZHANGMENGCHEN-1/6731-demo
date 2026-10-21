"""股东持股统计：保留主要股东、持股类型和报告期子表。"""


def get_shareholders_overview(client, code, period_id=None):
    return client.call("get_shareholders_overview", code, period_id=period_id)
