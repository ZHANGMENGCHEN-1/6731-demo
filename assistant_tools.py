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


def get_broker_net_summary(start_date=None, end_date=None, top_n=5):
    """Sum signed daily top-list observations, choosing history over realtime."""
    import math
    from datetime import timedelta
    from cloud_store import get_store, unpack_frame
    end = date.fromisoformat(end_date) if end_date else datetime.now(HK).date()
    start = date.fromisoformat(start_date) if start_date else end - timedelta(days=29)
    if start > end or (end - start).days > 366:
        raise ValueError("日期区间须为正序，且不能超过366天。")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 100:
        raise ValueError("top_n 必须为1到100。")
    chosen = {}
    for record in get_store().read_broker_net_records(start, end):
        day = record["record_date"]
        if not start <= date.fromisoformat(day) <= end:
            raise ValueError("返回的券商记录超出请求日期范围。")
        if day not in chosen or record["dataset"] == "broker_history":
            chosen[day] = record
    totals, covered, excluded, source_counts = {}, [], [], {}
    row_count = 0
    for day, record in sorted(chosen.items()):
        frame = unpack_frame(record["payload"])
        if frame.empty or not {"broker_name", "net_vol"}.issubset(frame.columns):
            excluded.append(day)
            continue
        metadata = record.get("metadata", {})
        if metadata.get("date_basis") == "trading_calendar_offset":
            offset = metadata.get("days_before")
            dates_ok = (isinstance(offset, int) and not isinstance(offset, bool) and offset > 0
                        and metadata.get("anchor", "") > day)
        elif "data_time_str" in frame:
            times = pd.to_datetime(frame.data_time_str, errors="coerce")
            dates_ok = times.notna().all() and times.dt.date.eq(date.fromisoformat(day)).all()
        else:
            dates_ok = False
        names = frame.broker_name
        values = pd.to_numeric(frame.net_vol, errors="coerce")
        if (not dates_ok or names.duplicated().any()
                or not names.map(lambda v: isinstance(v, str) and bool(v.strip())).all()
                or not values.map(math.isfinite).all()):
            excluded.append(day)
            continue
        covered.append(day)
        row_count += len(frame)
        source = record["dataset"]
        source_counts[source] = source_counts.get(source, 0) + 1
        for name, value in zip(names, values):
            entry = totals.setdefault(name, {"broker_name": name, "net_shares": 0, "observed_days": 0})
            entry["net_shares"] += float(value)
            entry["observed_days"] += 1
    return {"code": "HK.06731", "requested_start": str(start), "requested_end": str(end),
            "covered_dates": covered, "covered_days": len(covered), "excluded_dates": excluded,
            "row_count": row_count, "broker_count": len(totals), "unit": "股", "source_counts": source_counts,
            "net_buy": sorted((r for r in totals.values() if r["net_shares"] > 0),
                              key=lambda r: (-r["net_shares"], r["broker_name"]))[:top_n],
            "net_sell": sorted((r for r in totals.values() if r["net_shares"] < 0),
                               key=lambda r: (r["net_shares"], r["broker_name"]))[:top_n],
            "title": "近一个月每日十大榜内累计净买卖排名",
            "note": "按券商原始名称累计每日net_vol，正负相抵后排名；同日优先历史记录，不重复相加。"
                    "未上榜日净额未知，不补零；结果不是券商完整月度净额或全市场排名。"
                    "这是净买卖方向，不是买入量+卖出量或交易活跃度。"
                    "默认近30个自然日（含今天），不是30个交易日；仅汇总已保存日期，未核实完整交易日覆盖。"
                    "brokers来源是最后保存的当日累计快照，可能尚未收盘或已过时。"
                    "回答必须给出请求区间、实际覆盖天数和上述局限；无有效数据则明确说无法统计。"}


def get_broker_activity(start_date=None, end_date=None, metric="成交数量", top_n=10):
    """Aggregate saved daily gross activity, never substitute absolute net volume."""
    import calendar
    import math
    from cloud_store import get_store, unpack_frame
    end = date.fromisoformat(end_date) if end_date else datetime.now(HK).date()
    month = end.month - 1 or 12
    year = end.year - (end.month == 1)
    start = date.fromisoformat(start_date) if start_date else date(year, month, min(end.day, calendar.monthrange(year, month)[1]))
    if start > end or (end - start).days > 366:
        raise ValueError("日期区间须为正序，且不能超过366天。")
    if metric not in ("成交数量", "成交金额"):
        raise ValueError("活跃度只支持成交数量或成交金额，不使用净买卖量。")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 100:
        raise ValueError("top_n 必须为1到100。")
    field = "total_vol" if metric == "成交数量" else "total_turnover"
    totals, days, excluded = {}, [], []
    records = get_store().read_broker_activity_records(start, end)
    for record in records:
        frame = unpack_frame(record["payload"])
        day = record["record_date"]
        # A missing broker is unknown, never an observed zero. No historical fallback.
        if not {"broker_name", field, "data_time_str", "is_real_time"}.issubset(frame.columns) or frame.empty:
            excluded.append(day)
            continue
        times = pd.to_datetime(frame.data_time_str, errors="coerce")
        values = pd.to_numeric(frame[field], errors="coerce")
        names = frame.broker_name
        valid = (times.notna() & (times.dt.date == date.fromisoformat(day))
                 & frame.is_real_time.eq(True) & values.map(lambda v: math.isfinite(v) and v >= 0)
                 & names.map(lambda v: isinstance(v, str) and bool(v.strip())))
        if not valid.all() or names.duplicated().any():
            excluded.append(day)
            continue
        days.append(day)
        for name, value in zip(names, values):
            entry = totals.setdefault(name, {"broker_name": name, "activity": 0, "observed_days": 0})
            entry["activity"] += float(value)
            entry["observed_days"] += 1
    ranking = sorted(totals.values(), key=lambda row: (-row["activity"], row["broker_name"]))[:top_n]
    return {"code": "HK.06731", "requested_start": str(start), "requested_end": str(end),
            "metric": metric, "unit": "股" if metric == "成交数量" else "HKD",
            "ranking": ranking, "covered_dates": sorted(days), "covered_days": len(days),
            "excluded_dates": sorted(excluded), "saved_days": len(records),
            "coverage": "部分样本；未核实完整交易日覆盖", "source": "Supabase逐日保存的实时十大净买卖榜",
            "note": "按券商汇总total_vol（买入量+卖出量）或total_turnover，不是净买卖或其绝对值。"
                    "仅包含每日净买卖十大榜出现的券商；未上榜日视为未知，不补零。"
                    "每日保存的是最后一次采集快照，可能尚未收盘；不是全市场或完整月度排名。"
                    "历史接口不含总成交量/金额，无法补算；同名券商按原始名称归组。"
                    "无有效数据时明确说明无法回答，不改用净额榜。必须报告请求区间、覆盖日期和局限。"}


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
