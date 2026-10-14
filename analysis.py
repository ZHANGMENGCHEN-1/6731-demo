"""06731 本地真实 CCASS 快照的读取和规则分析。"""
from datetime import date
from pathlib import Path
import re
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
COLUMNS = ["participant_id", "participant_name", "address", "shares", "percentage"]


def discover_snapshots(data_dir=DATA_DIR):
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
