"""OpenD 连接、订阅及进程内调用限频。"""

from collections import defaultdict, deque
import os
from threading import RLock
import time


class SubscriptionError(RuntimeError):
    """必要订阅失败；保留 SDK 错误码和原始错误信息。"""

    def __init__(self, ret, data):
        self.ret = ret
        self.data = data
        super().__init__(f"OpenD subscription failed ({ret}): {data}")


class FutuClient:
    """一个连接供多个分类函数复用；建议用 with 管理生命周期。

    所有取数调用原样返回 SDK tuple，包含 ret 和原始 payload。
    默认每接口每 30 秒最多 10 次，是保守的客户端限制，不代表服务端额度。
    限频只覆盖本实例；不要并发创建大量实例绕过服务端限制。
    """

    def __init__(self, host=None, port=None, *, max_calls=10, window=30,
                 context_factory=None):
        if max_calls < 1 or window <= 0:
            raise ValueError("max_calls must be >= 1 and window must be > 0")
        self.host = host or os.getenv("FUTU_OPEND_HOST", "127.0.0.1")
        self.port = int(port if port is not None else os.getenv("FUTU_OPEND_PORT", "11111"))
        self.max_calls = max_calls
        self.window = window
        self._factory = context_factory
        self._context = None
        self._subscriptions = set()
        self._calls = defaultdict(deque)
        self._lock = RLock()

    def connect(self):
        with self._lock:
            if self._context is None:
                factory = self._factory
                if factory is None:
                    from futu import OpenQuoteContext
                    factory = OpenQuoteContext
                self._context = factory(host=self.host, port=self.port)
        return self

    def _throttle(self, method):
        calls = self._calls[method]
        while True:
            now = time.monotonic()
            while calls and now - calls[0] >= self.window:
                calls.popleft()
            if len(calls) < self.max_calls:
                calls.append(now)
                return
            time.sleep(max(0.001, self.window - (now - calls[0])))

    def call(self, method, *args, **kwargs):
        with self._lock:
            self.connect()
            self._throttle(method)
            return getattr(self._context, method)(*args, **kwargs)

    def subscribe(self, codes, subtype):
        """订阅本连接尚未订阅的 code/type；失败时禁止继续取数。"""
        with self._lock:
            missing = list(dict.fromkeys(code for code in codes
                                         if (code, subtype) not in self._subscriptions))
            if missing:
                ret, data = self.call("subscribe", missing, [subtype], subscribe_push=False)
                if ret != 0:
                    raise SubscriptionError(ret, data)
                self._subscriptions.update((code, subtype) for code in missing)

    def close(self):
        with self._lock:
            if self._context is not None:
                try:
                    self._context.close()
                finally:
                    self._context = None
                    self._subscriptions.clear()

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc, tb):
        self.close()
