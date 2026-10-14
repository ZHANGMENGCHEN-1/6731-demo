"""串行获取 HKEX 06731 CCASS 快照；异常停止，不生成替代数据。"""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import pandas as pd
import requests

URL = "https://www3.hkexnews.hk/sdw/search/searchsdw.aspx"
DATA = Path(__file__).resolve().parent / "data"
EXPECTED = {
    "A00005": ("CHINA SECURITIES DEPOSITORY AND CLEARING", 309717870, 83.80),
    "B01228": ("CITIC SECURITIES BROKERAGE (HK) LTD", 21868100, 5.91),
    "B01900": ("ORIENT SECURITIES (HONG KONG) LTD", 7842300, 2.12),
    "B01654": ("CHINA INTERNATIONAL CAPITAL CORPORATION", 4128900, 1.11),
    "B01138": ("CLSA LTD", 2985900, 0.80),
    "B01955": ("FUTU SECURITIES INTERNATIONAL", 2926810, 0.79),
    "C00010": ("CITIBANK N.A.", 2882969, 0.78),
}


def clean(text):
    return " ".join(text.split())


def check_response(response):
    response.raise_for_status()
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    if any(word in text for word in ("captcha", "access denied", "request rejected", "verify you are human", "too many requests", "unusual traffic")):
        raise ValueError("网站返回验证码、访问拒绝或反自动化限制，已停止，不尝试绕过。")
    return soup


def parse_snapshot(soup, requested_date):
    alert = soup.select_one("#alertMsg")
    message = clean(alert.get("value", "")) if alert else ""
    if message:
        if re.search(r"no (?:shareholding )?(?:record|data|information)|not found", message, re.I):
            return None
        raise ValueError(f"HKEX 返回提示：{message}")
    heading = soup.select_one(".search-bar__selectedItem-filter.searchDate")
    match = re.search(r"\d{4}/\d{2}/\d{2}", heading.get_text(" ", strip=True) if heading else "")
    if not match:
        raise ValueError("未找到结果日期，不能确认查询成功。")
    actual_date = date.fromisoformat(match.group().replace("/", "-"))
    if actual_date != requested_date:
        if actual_date < requested_date:
            return None  # HKEX 在部分非交易日返回前一日；禁止错标日期。
        raise ValueError(f"结果日期异常：请求 {requested_date}，返回 {actual_date}")
    # 结果股票标题位于 search-bar__selectedItem 内；不依赖输入框的回显。
    title_text = " ".join(x.get_text(" ", strip=True) for x in soup.select(".search-bar__selectedItem, .search-bar__selectedItem-stock"))
    if not re.search(r"\b06731\b", title_text):
        raise ValueError("结果股票标题不是 06731，已停止。")
    table = soup.select_one("table.table")
    if table is None:
        text = soup.get_text(" ", strip=True)
        if re.search(r"no (?:shareholding )?(?:record|data|information)", text, re.I):
            return None
        raise ValueError("未找到持仓明细表，返回结构异常。")
    selectors = ["col-participant-id", "col-participant-name", "col-address", "col-shareholding", "col-shareholding-percent"]
    records = []
    for row in table.select("tbody tr"):
        cells = [row.select_one(f".{col} .mobile-list-body") for col in selectors]
        if any(cell is None for cell in cells):
            raise ValueError("持仓表字段不完整。")
        pid, name, address, shares, percentage = [clean(cell.get_text(" ", strip=True)) for cell in cells]
        if not re.fullmatch(r"[A-Z]\d{5}", pid):
            raise ValueError(f"Participant ID 异常：{pid}")
        shares = int(shares.replace(",", ""))
        percentage = float(percentage.removesuffix("%"))
        if shares < 0 or not 0 <= percentage <= 100:
            raise ValueError(f"持仓数值异常：{pid}")
        records.append((pid, name, address, shares, percentage))
    df = pd.DataFrame(records, columns=["participant_id", "participant_name", "address", "shares", "percentage"])
    if df.empty or df.participant_id.duplicated().any():
        raise ValueError("明细为空或 Participant ID 重复。")
    counts = [int(x.get_text(strip=True).replace(",", "")) for x in soup.select(".number-of-participants .value")]
    totals = [int(x.get_text(strip=True).replace(",", "")) for x in soup.select(".shareholding .value")]
    if not counts or not totals or len(df) != counts[-1] or int(df.shares.sum()) != totals[-1]:
        raise ValueError("明细数量或股数合计与网页汇总不一致，拒绝保存。")
    return df


def validate_reference(df):
    rows = df.set_index("participant_id")
    for pid, (name, shares, percentage) in EXPECTED.items():
        if pid not in rows.index:
            raise ValueError(f"验收失败：缺少 {pid}")
        row = rows.loc[pid]
        if row.participant_name != name or int(row.shares) != shares or abs(float(row.percentage) - percentage) > 1e-8:
            raise ValueError(f"验收失败：{pid} 实际为 {row.to_dict()}")
    print("2026-10-13: 七条人工参考记录全部验收通过", flush=True)


def fetch_day(session, day):
    initial = session.get(URL, timeout=40)
    soup = check_response(initial)
    form = soup.find("form")
    if form is None:
        raise ValueError("查询表单缺失。")
    payload = {x["name"]: x.get("value", "") for x in form.select("input[name]")}
    for field in ("txtShareholdingDate", "txtStockCode"):
        if field not in payload:
            raise ValueError(f"实际表单已变化：缺少 {field}")
    button = form.select_one("#btnSearch")
    target = re.search(r"__doPostBack\('([^']+)'", button.get("href", "") if button else "")
    if not target:
        raise ValueError("无法识别实际查询按钮的回传参数。")
    payload.update(txtShareholdingDate=day.strftime("%Y/%m/%d"), txtStockCode="06731",
                   __EVENTTARGET=target.group(1), __EVENTARGUMENT="")
    response = session.post(urljoin(URL, form.get("action", "")), data=payload, timeout=40)
    # 保留原始响应用于排查错误和复核来源；不包含伪造数据。
    raw = DATA / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    response.encoding = "utf-8"
    (raw / f"hkex_{day}.html").write_text(response.text, encoding="utf-8")
    return parse_snapshot(check_response(response), day)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", choices=["06731"])
    parser.add_argument("start", type=date.fromisoformat)
    parser.add_argument("end", type=date.fromisoformat)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("开始日期不能晚于结束日期。")
    DATA.mkdir(exist_ok=True)
    results = []
    failure = None
    try:
        with requests.Session() as session:
            day = args.start
            while day <= args.end:
                df = fetch_day(session, day)
                if df is None:
                    print(f"{day}: 无数据，已跳过", flush=True)
                    results.append({"date": str(day), "status": "no_data"})
                else:
                    if day == date(2026, 10, 13):
                        validate_reference(df)
                    target = DATA / f"ccass_{day}.csv"
                    temporary = target.with_suffix(".csv.tmp")
                    df.to_csv(temporary, index=False, encoding="utf-8-sig")
                    temporary.replace(target)
                    print(f"{day}: 成功，获取 {len(df)} 个 Participant", flush=True)
                    results.append({"date": str(day), "status": "success", "participants": len(df), "shares": int(df.shares.sum())})
                day += timedelta(days=1)
                time.sleep(2.5)
    except (requests.RequestException, ValueError, OSError) as exc:
        failure = str(exc)
        print(f"抓取已停止：{exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        (DATA / "fetch_report.json").write_text(json.dumps({"stock": "06731", "source": URL,
            "start": str(args.start), "end": str(args.end), "error": failure, "results": results},
            ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
