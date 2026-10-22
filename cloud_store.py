"""Supabase REST 原始快照存储；密钥只在采集端或 Streamlit 服务端使用。"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
from threading import RLock
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)
if not (ROOT / ".env").exists():
    load_dotenv(ROOT / ".ENV", override=False)
TABLE = "market_data_snapshots"


class CloudDataError(ValueError):
    pass


def setting(name, default=None):
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except (FileNotFoundError, KeyError):
        return default


def uses_cloud():
    backend = str(setting("DATA_BACKEND", "local")).lower()
    if backend not in ("local", "supabase"):
        raise CloudDataError("DATA_BACKEND 只支持 local 或 supabase")
    return backend == "supabase"


def pack_frame(frame):
    # pandas 负责将 NaN 转 null；15 位小数保留原接口精度，不导出展示格式。
    data = json.loads(frame.to_json(orient="split", index=False, date_format="iso", double_precision=15))
    return {"columns": data["columns"], "data": data["data"]}


def unpack_frame(payload):
    if not isinstance(payload, dict) or not {"columns", "data"}.issubset(payload):
        raise CloudDataError("云端快照格式不完整")
    return pd.DataFrame(payload["data"], columns=payload["columns"])


@dataclass(frozen=True)
class CloudSnapshot:
    day: date


class SupabaseStore:
    def __init__(self, url, key, *, read_only=True, bearer=None):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".supabase.co") or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip("/") not in ("", "/rest/v1") or parsed.port not in (None, 443):
            raise CloudDataError("SUPABASE_URL 必须是有效的 https://项目.supabase.co 地址")
        if not key:
            raise CloudDataError("缺少 Supabase 服务端连接密钥")
        self.url = f"https://{parsed.netloc}/rest/v1/{TABLE}"
        self._headers = {"apikey": key}
        if bearer or key.startswith("eyJ"):
            self._headers["Authorization"] = "Bearer " + (bearer or key)
        self.read_only = read_only
        self._cache = {}
        self._lock = RLock()

    def _request(self, method, *, params=None, body=None, extra_headers=None):
        headers = {**self._headers, **(extra_headers or {})}
        try:
            response = requests.request(method, self.url, headers=headers, params=params,
                                        json=body, timeout=(5, 25), allow_redirects=False)
        except requests.RequestException:
            raise CloudDataError("Supabase 连接失败，请检查网络及项目是否处于运行状态。") from None
        if not 200 <= response.status_code < 300:
            if response.status_code == 404:
                hint = "业务表尚未就绪，请先执行 supabase/schema.sql。"
            elif response.status_code in (401, 403):
                hint = "连接密钥或读取权限不足，请核对 Supabase 服务端配置。"
            else:
                hint = "请求未完成，请检查项目状态、表结构与额度。"
            # 不回显 URL、请求头或响应原文，避免错误日志暴露凭据。
            raise CloudDataError(f"Supabase HTTP {response.status_code}：{hint}")
        return response.json() if response.content else None

    def _get(self, params):
        key = json.dumps(params, sort_keys=True)
        with self._lock:
            cached = self._cache.get(key)
            if cached and time.monotonic() - cached[0] < 30:
                return cached[1]
        data = self._request("GET", params=params)
        with self._lock:
            self._cache[key] = (time.monotonic(), data)
        return data

    def check(self):
        self._request("GET", params={"select": "dataset", "limit": 1})

    def dates(self, dataset, code="HK.06731"):
        result, offset = [], 0
        while True:
            page = self._get({"select": "record_date", "dataset": "eq." + dataset, "code": "eq." + code,
                              "order": "record_date.asc", "limit": 100, "offset": offset})
            result.extend(date.fromisoformat(row["record_date"]) for row in page)
            if len(page) < 100:
                return result
            offset += len(page)

    def read(self, dataset, day=None, code="HK.06731"):
        params = {"select": "*", "dataset": "eq." + dataset, "code": "eq." + code,
                  "order": "record_date.desc,fetched_at.desc", "limit": 1}
        if day is not None:
            params["record_date"] = "eq." + str(day)
        rows = self._get(params)
        if not rows:
            raise CloudDataError(f"云端还没有 {dataset}{' / ' + str(day) if day else ''} 数据，请运行本机同步程序。")
        row = rows[0]
        return unpack_frame(row["payload"]), row

    def write(self, dataset, day, frame, *, code="HK.06731", metadata=None, fetched_at=None):
        if self.read_only:
            raise CloudDataError("网页数据连接仅允许读取")
        if frame.empty:
            raise CloudDataError(f"{dataset} 为空，保留上一次成功快照，不覆盖")
        body = {"dataset": dataset, "code": code, "record_date": str(day), "payload": pack_frame(frame),
                "metadata": metadata or {}, "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat()}
        self._request("POST", params={"on_conflict": "dataset,code,record_date"}, body=body,
                      extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"})
        with self._lock:
            self._cache.clear()


@lru_cache(maxsize=4)
def _store(url, key, read_only, bearer):
    return SupabaseStore(url, key, read_only=read_only, bearer=bearer)


def get_store(*, writer=False):
    key = setting("SUPABASE_SECRET_KEY", "") if writer else setting("SUPABASE_READ_KEY") or setting("SUPABASE_SECRET_KEY", "")
    return _store(setting("SUPABASE_URL", ""), key, not writer, setting("SUPABASE_READ_ACCESS_TOKEN") if not writer else None)
