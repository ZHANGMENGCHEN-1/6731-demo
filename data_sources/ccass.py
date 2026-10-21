"""复用项目现有 HKEX CCASS 抓取路径；当前仅支持 06731。"""

from datetime import date

import requests

from fetch_ccass import fetch_day


def get_ccass(stock_code, day, *, session=None):
    """返回原始解析 DataFrame；无对应日期数据返回 None，失败抛原异常。

    沿用 fetch_day 的 HTML 留档副作用，不保存 CSV、不改写日期、不计算持仓变化。
    """
    if stock_code not in ("06731", "HK.06731"):
        raise ValueError("现有 CCASS 抓取器仅支持 06731")
    if isinstance(day, str):
        day = date.fromisoformat(day)
    if type(day) is not date:
        raise TypeError("day must be datetime.date or YYYY-MM-DD")
    if session is not None:
        return fetch_day(session, day)
    with requests.Session() as owned_session:
        return fetch_day(owned_session, day)
