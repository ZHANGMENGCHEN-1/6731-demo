"""外部定时器入口：python fetch_latest.py；单次更新后退出。"""
from datetime import date, datetime, timedelta, timezone
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tempfile
import time

import requests
from analysis import discover_snapshots
import fetch_ccass

LISTING_DATE = date(2026, 9, 29)
LOGGER = logging.getLogger("ccass.update")


def latest_available_date(session):
    """读取 HKEX 实际查询表单默认日期，不把本地今天/昨天当发布日期。"""
    soup = fetch_ccass.check_response(session.get(fetch_ccass.URL, timeout=40))
    field = soup.select_one('form input[name="txtShareholdingDate"]')
    if field is None:
        raise ValueError("HKEX 查询页缺少最新持仓日期字段，已停止更新。")
    try:
        day = datetime.strptime(field.get("value", "").strip(), "%Y/%m/%d").date()
    except ValueError:
        raise ValueError("HKEX 查询页日期格式异常，已停止更新。") from None
    today = datetime.now(timezone(timedelta(hours=8))).date()
    if day > today:
        raise ValueError("HKEX 返回未来日期，无法确认最新可用日期。")
    return day


def save_new_snapshot(frame, day, data_dir):
    """先完整写临时文件，再原子发布；即使同时执行也不覆盖已有 CSV。"""
    target = data_dir / f"ccass_{day}.csv"
    if target.exists():
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="", dir=data_dir,
                                         prefix=".ccass_", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            frame.to_csv(stream, index=False)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            return False
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update_latest(data_dir=None):
    data_dir = Path(data_dir) if data_dir is not None else fetch_ccass.DATA
    day = None
    saved = 0
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        snapshots = discover_snapshots(data_dir)
        local_latest = max(snapshots) if snapshots else None
        LOGGER.info("当前本地最新数据：%s", local_latest or "暂无，将从上市日补齐")
        with requests.Session() as session:
            published = latest_available_date(session)
            LOGGER.info("HKEX 查询页最新可用日期：%s", published)
            if local_latest is not None and local_latest >= published:
                LOGGER.info("当前已是最新数据，无需更新。")
                return 0
            day = local_latest + timedelta(days=1) if local_latest else LISTING_DATE
            while day <= published:
                target = data_dir / f"ccass_{day}.csv"
                if target.exists():
                    LOGGER.info("%s: 已存在，保留原文件", day)
                    day += timedelta(days=1)
                    continue
                # 发现日期、抓取、日期核对和汇总校验均使用原抓取器。
                frame = fetch_ccass.fetch_day(session, day)
                if frame is None:
                    LOGGER.info("%s: 无数据，已跳过（休市或尚未发布不视为错误）", day)
                else:
                    if day == date(2026, 10, 13):
                        fetch_ccass.validate_reference(frame)
                    LOGGER.info("发现新数据：%s；抓取成功：%s Participants", day, len(frame))
                    if save_new_snapshot(frame, day, data_dir):
                        saved += 1
                        LOGGER.info("%s: 保存完成", target.name)
                    else:
                        LOGGER.info("%s: 已由其他任务保存，保留原文件", day)
                time.sleep(2.5)
                day += timedelta(days=1)
        if saved:
            LOGGER.info("更新完成，共保存 %s 个新日期。看板下次刷新自动读取。", saved)
        else:
            LOGGER.info("HKEX 尚无新的 06731 日期快照，保留历史数据，无需更新。")
        return 0
    except (requests.RequestException, ValueError, OSError, OverflowError) as exc:
        LOGGER.error("更新失败%s：%s；已有 CSV 未覆盖，历史看板可继续使用。", f"（{day}）" if day else "", exc)
        return 1


def main():
    log_dir = Path(__file__).resolve().parent / "logs"
    try:
        log_dir.mkdir(exist_ok=True)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        formatter.converter = lambda timestamp: datetime.fromtimestamp(timestamp, timezone(timedelta(hours=8))).timetuple()
        LOGGER.setLevel(logging.INFO)
        LOGGER.propagate = False
        for handler in list(LOGGER.handlers):
            LOGGER.removeHandler(handler)
            handler.close()
        for handler in (logging.StreamHandler(sys.stdout), RotatingFileHandler(
                log_dir / "fetch_latest.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")):
            handler.setFormatter(formatter)
            LOGGER.addHandler(handler)
        LOGGER.info("开始检查 06731 CCASS 更新")
        return update_latest()
    except OSError as exc:
        print(f"无法初始化更新日志：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
