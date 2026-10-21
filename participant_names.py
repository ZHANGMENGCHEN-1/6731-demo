"""HKEX 官方 CCASS 名录的展示名称；不跨来源合并经纪实体。"""
from functools import lru_cache
import json
from pathlib import Path
import re

REFERENCE = Path(__file__).resolve().parent / "data" / "reference"
SOURCE_DATE = "2026-10-20"
SOURCE_URL = "https://www3.hkexnews.hk/sdw/search/ccass_part_list_c.htm?sortby=partid&shareholdingdate=20261020"


@lru_cache(maxsize=1)
def directory():
    """只读已下载名录，页面不发起网络请求。"""
    tables = []
    for language in ("en", "zh"):
        rows = json.loads((REFERENCE / f"ccass_participants_20261020_{language}.json").read_text(encoding="utf-8-sig"))
        table = {row["c"]: row["n"] for row in rows}
        if len(table) != len(rows):
            raise ValueError("CCASS 参考名录包含重复参与者编号")
        tables.append(table)
    return tuple(tables)


def chinese_name(participant_id, original_name):
    english, chinese = directory()
    canonical = english.get(str(participant_id), "")
    normalize = lambda text: re.sub(r"[^A-Z0-9]", "", str(text).upper())
    original = normalize(original_name)
    # 本地 HKEX 名称可能截断；编号相同且英文前缀一致才允许显示。
    if not original or not normalize(canonical).startswith(original):
        return ""
    value = chinese.get(str(participant_id), "")
    return value if re.search(r"[\u3400-\u9fff]", value) else ""


def display_name(participant_id, original_name):
    translated = chinese_name(participant_id, original_name)
    return f"{translated} / {original_name}" if translated else str(original_name)
