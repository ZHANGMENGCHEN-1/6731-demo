"""AI 只读查询工具；复用各页面的数据路径和计算口径。"""
from datetime import date, datetime
from zoneinfo import ZoneInfo
import socket

import pandas as pd

import analysis

HK = ZoneInfo("Asia/Hong_Kong")


def _sync_metadata(fetched_at):
    now = datetime.now(HK)
    fetched = datetime.fromisoformat(fetched_at).astimezone(HK)
    age = max(0, int((now - fetched).total_seconds()))
    return {"query_time_hk": now.isoformat(), "sync_age_seconds": age,
            "freshness_note": "同步已超过3分钟，只能视为最近保存的数据，不是当前实时状态。" if age > 180 else "以原始更新时间为准。"}


def _latest_day_only(target_date):
    if target_date and date.fromisoformat(target_date) != datetime.now(HK).date():
        raise ValueError("此工具仅查询最近可用行情/成交样本，不支持指定历史日期。")


def get_market_quote(include_intraday=False, target_date=None):
    if not isinstance(include_intraday, bool):
        raise ValueError("include_intraday 必须为布尔值。")
    _latest_day_only(target_date)
    from views.market_home import load_market_home
    data = load_market_home()
    if "snapshot" not in data:
        raise ValueError("行情暂不可用：" + data.get("errors", {}).get("snapshot", data.get("errors", {}).get("connection", "无数据")))
    result = {"code": "HK.06731", "source": data.get("backend", "OpenD"),
              "fetched_at": data["fetched_at"], "timezone": "Asia/Hong_Kong",
              "snapshot": data["snapshot"], "errors": data.get("errors", {}),
              "note": "最近可用行情，休市时可能是上一交易日；实际更新时间以原始字段为准。"}
    result.update(_sync_metadata(data["fetched_at"]))
    if include_intraday:
        result["intraday"] = data.get("intraday")
    return result


def get_broker_net_trades(target_date=None, top_n=10):
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 10:
        raise ValueError("券商榜单 top_n 必须为1到10。")
    from views.market_home import load_market_home, split_brokers
    if target_date:
        from views.broker_history import query_cloud_brokers, query_brokers_on_date
        from cloud_store import uses_cloud
        target = date.fromisoformat(target_date)
        if uses_cloud():
            data = query_cloud_brokers(target)
        else:
            from data_sources import FutuClient
            client = FutuClient()
            with socket.create_connection((client.host, client.port), timeout=2):
                pass
            with client:
                data = query_brokers_on_date(client, target)
        frame = data["frame"]
    else:
        data = load_market_home()
        frame = data.get("brokers")
        if frame is None or frame.empty:
            raise ValueError("最近可用券商净买卖数据为空，请检查同步状态或 OpenD。")
    buys, sells = split_brokers(frame)
    return {"code": "HK.06731", "trade_date": target_date,
            "date_basis": "交易日历与 days_before 换算" if target_date else "最近可用实时累计榜单",
            "fetched_at": data["fetched_at"], **_sync_metadata(data["fetched_at"]),
            "net_buy": buys.head(top_n), "net_sell": sells.head(top_n),
            "note": "net_vol 单位为股。券商渠道不等于自营或最终投资者；净买卖不等于CCASS持仓变化。data_time_str为原始更新时间。"}


def get_recent_trade_ranking(limit=20, direction="全部", sort="成交数量", target_date=None):
    _latest_day_only(target_date)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("逐笔排名 limit 必须为1到100。")
    if direction not in ("全部", "主动买入", "主动卖出", "中性") or sort not in ("成交数量", "成交金额"):
        raise ValueError("逐笔成交方向或排序方式无效。")
    from views.trade_ticker import load_recent_trades, rank_recent_trades
    frame, fetched_at = load_recent_trades()
    if frame.empty:
        raise ValueError("最近逐笔样本为空。")
    times = pd.to_datetime(frame.time, errors="coerce")
    return {"code": "HK.06731", "fetched_at": fetched_at, **_sync_metadata(fetched_at), "sample_count": len(frame),
            "sample_start": str(times.min()), "sample_end": str(times.max()),
            "direction": direction, "sort": sort,
            "ranking": rank_recent_trades(frame, direction, sort, limit),
            "note": "只对最近最多1000笔样本排名，不是全天Top排名；不含成交券商或对手券商身份。价格/金额单位HKD，数量单位股。"}


def compare_participant_holdings(participants, start_date, end_date):
    if not isinstance(participants, list) or not 1 <= len(participants) <= 8 or not all(isinstance(p, str) and p.strip() for p in participants):
        raise ValueError("请提供1到8个参与者编号或明确名称。")
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if start > end:
        raise ValueError("开始日期不能晚于结束日期。")
    data = analysis.get_monitoring_data()
    frames = data["frames"]
    if start not in frames or end not in frames:
        raise ValueError("所选起止日期没有真实CCASS快照，不自动替换日期。")
    from participant_names import chinese_name
    names = pd.concat(frames.values()).drop_duplicates("participant_id", keep="last")
    labels = {row.participant_id: (row.participant_name, chinese_name(row.participant_id, row.participant_name))
              for row in names.itertuples()}
    selected = []
    for value in participants:
        value = value.strip()
        matches = [pid for pid, aliases in labels.items()
                   if value.upper() == pid or any(value.casefold() in str(alias).casefold() for alias in aliases if alias)]
        if len(matches) != 1:
            raise ValueError(f"参与者“{value}”无法唯一确定，请提供参与者编号。候选：{', '.join(matches[:8]) or '无'}")
        if matches[0] not in selected:
            selected.append(matches[0])
    from views.participant_comparison import comparison_data, relative_history
    history, summary = comparison_data(frames, selected, start, end)
    return {"start_date": start_date, "end_date": end_date, "source": "HKEX CCASS",
            "summary": summary, "history": relative_history(history),
            "note": "结算后参与者持仓，不等于最终股东或交易方向；缺席不补零，变化按区间首日基准计算。"}
