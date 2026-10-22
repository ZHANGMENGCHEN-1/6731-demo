"""本机运行：OpenD 采集上传 Supabase；不需要打开 Streamlit 页面。"""
import argparse
from datetime import date, datetime, timedelta, timezone
import logging
import socket
import time

import pandas as pd

from cloud_store import CloudDataError, get_store
from data_sources import FutuClient, brokers, market

LOGGER = logging.getLogger("supabase.sync")
CODE = "HK.06731"


def frame_date(frame, field):
    if frame.empty or field not in frame:
        raise ValueError(f"缺少 {field}，不能确认源数据日期")
    dates = pd.to_datetime(frame[field], errors="coerce").dropna()
    if dates.empty:
        raise ValueError(f"{field} 无有效时间，未上传")
    return dates.max().date()


def sync_ccass(store):
    # 显式传本地目录，避免采集端意外读取云端作为上传来源。
    from analysis import DATA_DIR, discover_snapshots, load_snapshot
    uploaded = set(store.dates("ccass"))
    count = 0
    for day, path in discover_snapshots(DATA_DIR).items():
        if day not in uploaded:
            frame = load_snapshot(path)
            store.write("ccass", day, frame, metadata={"source": "HKEX CCASS", "file": path.name})
            count += 1
    LOGGER.info("CCASS 同步完成：新增 %s 个日期", count)


def sync_futu(store, history_days=30):
    errors = []
    client = FutuClient()
    with socket.create_connection((client.host, client.port), timeout=2):
        pass
    latest_brokers = None
    with client:
        for dataset, time_field, query in (
            ("snapshot", "update_time", lambda: market.get_market_snapshot(client, CODE)),
            ("brokers", "data_time_str", lambda: brokers.get_top_ten_buy_sell_brokers(client, CODE, days_before=0)),
            ("intraday", "time", lambda: market.get_rt_data(client, CODE)),
            ("ticker", "time", lambda: market.get_rt_ticker(client, CODE, num=1000)),
        ):
            try:
                ret, frame = query()
                if ret != 0:
                    raise ValueError("OpenD 未返回成功数据，请在本机检查行情权限")
                fetched_at = datetime.now(timezone.utc).isoformat()
                day = frame_date(frame, time_field)
                store.write(dataset, day, frame, fetched_at=fetched_at,
                            metadata={"source": "Futu OpenD", "time_field": time_field})
                if dataset == "brokers":
                    latest_brokers = frame
                LOGGER.info("%s 同步成功：日期 %s，%s 行", dataset, day, len(frame))
            except (ValueError, OSError) as exc:
                errors.append(dataset)
                LOGGER.warning("%s 未更新：%s", dataset, exc)
        if latest_brokers is not None and history_days:
            anchor = frame_date(latest_brokers, "data_time_str")
            start = max(date(2026, 9, 29), anchor - timedelta(days=min(365, history_days * 2 + 14)))
            ret, calendar = client.call("request_trading_days", code=CODE, start=str(start), end=str(anchor))
            if ret != 0:
                raise ValueError("历史券商交易日历获取失败")
            days = sorted({date.fromisoformat(row["time"]) for row in calendar})
            if not days or days[-1] != anchor:
                raise ValueError("券商基准日期与交易日历不一致")
            uploaded = set(store.dates("broker_history"))
            for offset, day in enumerate(reversed(days)):
                if offset == 0 or day in uploaded:
                    continue
                if offset > history_days:
                    break
                ret, frame = brokers.get_top_ten_buy_sell_brokers(client, CODE, days_before=offset)
                if ret != 0 or frame.empty:
                    LOGGER.warning("历史券商 %s 暂无可同步数据", day)
                    continue
                frame_date(frame, "data_time_str")  # 原始更新时间不等同于历史交易日期。
                store.write("broker_history", day, frame, metadata={"source": "Futu OpenD", "anchor": str(anchor), "days_before": offset, "date_basis": "trading_calendar_offset"})
                LOGGER.info("历史券商 %s 同步成功", day)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="只同步一次后退出")
    parser.add_argument("--check", action="store_true", help="只检查配置和业务表连通性")
    parser.add_argument("--interval", type=int, default=60, help="行情同步间隔秒数，最小30")
    parser.add_argument("--history-days", type=int, default=30, help="补齐最近 N 个交易日的历史券商记录")
    parser.add_argument("--ccass-only", action="store_true", help="只上传本地 CCASS，不连接 OpenD")
    parser.add_argument("--update-ccass", action="store_true", help="每15分钟最多增量抓取一次 CCASS 后上传")
    args = parser.parse_args()
    if args.interval < 30 or not 0 <= args.history_days <= 250:
        parser.error("interval 必须至少30秒，history-days 范围为0到250")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    store = get_store(writer=True)
    try:
        store.check()
    except CloudDataError as exc:
        LOGGER.error("%s", exc)
        return 1
    if args.check:
        LOGGER.info("Supabase 配置及业务表检查通过（未输出密钥）")
        return 0
    last_ccass_check = None
    while True:
        failed = False
        try:
            if args.update_ccass and (last_ccass_check is None or time.monotonic() - last_ccass_check >= 900):
                from fetch_latest import main as update_ccass
                last_ccass_check = time.monotonic()
                if update_ccass() != 0:
                    LOGGER.warning("CCASS 抓取未完成，仍同步已有本地快照")
            sync_ccass(store)
        except (ValueError, OSError) as exc:
            failed = True
            LOGGER.error("CCASS 同步未完成：%s", exc)
        if not args.ccass_only:
            try:
                failed = bool(sync_futu(store, args.history_days)) or failed
            except (ValueError, OSError):
                failed = True
                LOGGER.error("OpenD 同步未完成，请确认本机 OpenD 已启动并登录；下轮重试。")
        if args.once:
            return int(failed)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
