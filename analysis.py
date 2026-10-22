"""06731 本地真实 CCASS 快照的读取和规则分析。"""
from datetime import date
from pathlib import Path
import re
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
COLUMNS = ["participant_id", "participant_name", "address", "shares", "percentage"]


def discover_snapshots(data_dir=None):
    if data_dir is None:
        from cloud_store import uses_cloud, get_store, CloudSnapshot
        if uses_cloud():
            return {day: CloudSnapshot(day) for day in get_store().dates("ccass")}
        data_dir = DATA_DIR
    snapshots = {}
    for path in Path(data_dir).glob("ccass_*.csv"):
        match = re.fullmatch(r"ccass_(\d{4}-\d{2}-\d{2})\.csv", path.name)
        if match:
            try:
                snapshots[date.fromisoformat(match.group(1))] = path
            except ValueError:
                continue
    return dict(sorted(snapshots.items()))


def load_snapshot(path):
    from cloud_store import CloudSnapshot, get_store
    if isinstance(path, CloudSnapshot):
        df, _ = get_store().read("ccass", path.day)
    else:
        df = pd.read_csv(path, dtype={"participant_id": str, "participant_name": str, "address": str}, keep_default_na=False)
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"CSV 缺少字段：{', '.join(sorted(missing))}")
    df = df[COLUMNS].copy()
    if df.empty:
        raise ValueError("CSV 不能为空。")
    for col in ("participant_id", "participant_name", "address"):
        df[col] = df[col].map(lambda value: " ".join(value.split()))
    if df.participant_id.eq("").any() or df.participant_name.eq("").any() or df.participant_id.duplicated().any():
        raise ValueError("Participant ID 和名称不能为空，ID 不能重复。")
    for col in ("shares", "percentage"):
        df[col] = pd.to_numeric(df[col], errors="raise")
        if not df[col].between(0, float("inf"), inclusive="left").all():
            raise ValueError(f"{col} 必须是有限非负数。")
    if df.shares.mod(1).ne(0).any() or df.percentage.gt(100).any():
        raise ValueError("股数必须为整数，占比必须在 0 到 100 之间。")
    df["shares"] = df.shares.astype("int64")
    return df


def compare_snapshots(before, after):
    result = before.merge(after, on="participant_id", how="outer", suffixes=("_start", "_end"))
    for col in ("participant_name", "address"):
        result[col] = result[f"{col}_end"].combine_first(result[f"{col}_start"])
    for col in ("shares", "percentage"):
        for side in ("start", "end"):
            result[f"{side}_{col}"] = result[f"{col}_{side}"].fillna(0)
            if col == "shares":
                result[f"{side}_{col}"] = result[f"{side}_{col}"].astype("int64")
        result[f"{col}_change"] = result[f"end_{col}"] - result[f"start_{col}"]
    return result[["participant_id", "participant_name", "address", "start_shares", "end_shares", "shares_change",
                   "start_percentage", "end_percentage", "percentage_change"]].sort_values(
                       ["shares_change", "participant_id"], ascending=[False, True]).reset_index(drop=True)


def top_changes(comparison):
    return (comparison[comparison.shares_change > 0].nlargest(10, "shares_change"),
            comparison[comparison.shares_change < 0].nsmallest(10, "shares_change"))


def make_summary(comparison, start, end):
    up, down = top_changes(comparison)
    parts = [f"{start} 至 {end}，共有 {(comparison.shares_change > 0).sum()} 家 Participant 持仓增加，"
             f"{(comparison.shares_change < 0).sum()} 家持仓减少，{(comparison.shares_change == 0).sum()} 家不变。"]
    leaders = []
    if not up.empty:
        r = up.iloc[0]
        leaders.append(f"{r.participant_name}（{r.participant_id}）增加 {r.shares_change:,} 股，为持仓增加最多的 Participant")
    if not down.empty:
        r = down.iloc[0]
        leaders.append(f"{r.participant_name}（{r.participant_id}）减少 {-r.shares_change:,} 股，为持仓减少最多的 Participant")
    if leaders:
        parts.append("；".join(leaders) + "。")
    parts.append("仅凭这些结算后持仓变化不能确认 Participant 之间存在直接筹码转移关系，也不能推断最终投资者买卖或实时成交方向。")
    return "".join(parts)


def make_home_summary(comparison):
    """首页规则摘要；所有数量及集中度由 Python 计算，不调用 LLM。"""
    positive = comparison[comparison.shares_change > 0]
    negative = comparison[comparison.shares_change < 0]
    unchanged = int((comparison.shares_change == 0).sum())
    if positive.empty and negative.empty:
        return [f"所选区间 {len(comparison)} 家 Participant 的持股数量均未发生变化。",
                "没有持股数量增加或减少的机构；占比变化请查看明细。"]

    leaders = []
    concentration = []
    for frame, direction in ((positive, "增加"), (negative, "减少")):
        if frame.empty:
            leaders.append(f"没有持股数量{direction}的 Participant")
            continue
        magnitude = frame.shares_change.abs()
        maximum = int(magnitude.max())
        tied = frame[magnitude == maximum].sort_values("participant_id")
        row = tied.iloc[0]
        name = f"{row.participant_name}（{row.participant_id}）"
        suffix = f"等 {len(tied)} 家并列" if len(tied) > 1 else ""
        leaders.append(f"{name}{suffix}持仓{direction}最多，{'各' if len(tied) > 1 else ''}{direction} {maximum:,} 股")
        total = int(magnitude.sum())
        count = min(3, len(frame))
        share = float(magnitude.nlargest(count).sum()) / total * 100
        concentration.append(f"持仓{direction}前 {count} 家占全部{direction}股数的 {share:.1f}%")
    net = int(comparison.shares_change.sum())
    net_text = f"增加 {net:,} 股" if net > 0 else f"减少 {-net:,} 股" if net < 0 else "无变化"
    return ["；".join(leaders) + "。", "；".join(concentration) + "。",
            f"共 {len(positive)} 家持仓增加、{len(negative)} 家减少、{unchanged} 家不变，样本持股合计净变化为{net_text}。"]


def get_dataset_info():
    dates = [day.isoformat() for day in discover_snapshots()]
    return {"stock_code": "06731", "listing_date": "2026-09-29", "dates": dates,
            "date_count": len(dates), "earliest_date": dates[0] if dates else None,
            "latest_date": dates[-1] if dates else None,
            "persistent_definition": PERSISTENT_DEFINITION}


def compare_dates(start_date, end_date):
    start = date.fromisoformat(str(start_date))
    end = date.fromisoformat(str(end_date))
    snapshots = discover_snapshots()
    if start >= end:
        raise ValueError("开始日期必须早于结束日期。")
    if start not in snapshots or end not in snapshots:
        raise ValueError("所选日期没有本地真实快照。")
    return compare_snapshots(load_snapshot(snapshots[start]), load_snapshot(snapshots[end]))


def _check_top_n(top_n):
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n 必须是正整数。")


def get_top_increases(start_date, end_date, top_n=10):
    _check_top_n(top_n)
    comparison = compare_dates(start_date, end_date)
    return comparison[comparison.shares_change > 0].nlargest(top_n, "shares_change")


def get_top_decreases(start_date, end_date, top_n=10):
    _check_top_n(top_n)
    comparison = compare_dates(start_date, end_date)
    return comparison[comparison.shares_change < 0].nsmallest(top_n, "shares_change")


def get_participant_history(participant_id):
    participant_id = participant_id.strip().upper()
    if not re.fullmatch(r"[A-Z]\d{5}", participant_id):
        raise ValueError("Participant ID 格式应类似 B01228。")
    records = []
    for day, path in discover_snapshots().items():
        row = load_snapshot(path).set_index("participant_id")
        if participant_id in row.index:
            item = row.loc[participant_id]
            records.append({"date": str(day), "participant_id": participant_id, **item.to_dict(), "present": True})
        else:
            records.append({"date": str(day), "participant_id": participant_id, "participant_name": "",
                            "address": "", "shares": 0, "percentage": 0.0, "present": False})
    result = pd.DataFrame(records, columns=["date", *COLUMNS, "present"])
    result["shares_change"] = result.shares.diff().astype("Int64")
    return result


PERSISTENT_DEFINITION = ("近期持续趋势：取最近最多 6 个已有工作日快照（5 个区间），至少 3 个区间同向变化，"
                         "同向变化量占总绝对变化量至少 70%，且窗口净变化同向；允许不变和小幅反向变化。"
                         "至少需要 4 个工作日快照。缺席按零；仅为持仓趋势筛选，不代表买卖。")


def _persistent_from_frames(snapshots, direction):
    recent = [(day, frame) for day, frame in snapshots.items() if day.weekday() < 5][-6:]
    extra = ["interval_count", "direction_count", "direction_share", "window_start", "window_end"]
    if len(recent) < 4:
        return pd.DataFrame(columns=["participant_id", "participant_name", "address", "start_shares", "end_shares",
                                     "shares_change", "start_percentage", "end_percentage", "percentage_change", *extra])
    frames = [frame for _, frame in recent]
    matrix = pd.concat([frame.set_index("participant_id").shares for frame in frames], axis=1).fillna(0)
    delta = matrix.diff(axis=1).iloc[:, 1:]
    signed = delta if direction == "increase" else -delta
    counts = (signed > 0).sum(axis=1)
    gross = delta.abs().sum(axis=1)
    share = signed.clip(lower=0).sum(axis=1).div(gross.where(gross != 0))
    net = matrix.iloc[:, -1] - matrix.iloc[:, 0]
    eligible = (counts >= 3) & (share >= .7) & ((net > 0) if direction == "increase" else (net < 0))
    result = compare_snapshots(frames[0], frames[-1])
    result = result[result.participant_id.isin(matrix.index[eligible])].copy()
    result["interval_count"] = len(frames) - 1
    result["direction_count"] = result.participant_id.map(counts)
    result["direction_share"] = result.participant_id.map(share).mul(100)
    result["window_start"] = str(recent[0][0])
    result["window_end"] = str(recent[-1][0])
    return result.sort_values("shares_change", ascending=direction != "increase").reset_index(drop=True)


def _persistent_changes(direction):
    return _persistent_from_frames({day: load_snapshot(path) for day, path in discover_snapshots().items()}, direction)


def get_persistent_increases():
    return _persistent_changes("increase")


def get_persistent_decreases():
    return _persistent_changes("decrease")


def get_monitoring_data():
    """看板一次读取本地快照，复用既有对比计算。工作日仅按周一至周五筛选。"""
    frames = {day: load_snapshot(path) for day, path in discover_snapshots().items()}
    dates = list(frames)
    weekdays = [day for day in dates if day.weekday() < 5]
    recent = weekdays[-6:]
    return {"frames": frames, "dates": dates, "workdays": weekdays,
            "latest_snapshot_comparison": compare_snapshots(frames[dates[-2]], frames[dates[-1]]) if len(dates) >= 2 else None,
            "latest_comparison": compare_snapshots(frames[weekdays[-2]], frames[weekdays[-1]]) if len(weekdays) >= 2 else None,
            "listing_comparison": compare_snapshots(frames[dates[0]], frames[dates[-1]]) if len(dates) >= 2 else None,
            "persistent_increases": _persistent_from_frames(frames, "increase"),
            "persistent_decreases": _persistent_from_frames(frames, "decrease"),
            "persistent_window": (recent[0], recent[-1]) if recent else None}
