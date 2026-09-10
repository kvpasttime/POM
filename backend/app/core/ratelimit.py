# -*- coding: utf-8 -*-
"""登录限速（R-AUTH-11/12）：账号 5 次/15 分钟锁定；IP 10 次/分钟。进程内实现（单机部署）。"""
import time
from collections import defaultdict, deque

from app.core.config import get_settings


class LoginRateLimiter:
    def __init__(self):
        self._fails: dict[str, deque] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}
        self._ip_hits: dict[str, deque] = defaultdict(deque)

    def is_locked(self, username: str) -> int:
        """返回剩余锁定秒数，0 表示未锁定"""
        until = self._locked_until.get(username, 0)
        if until <= time.time():
            return 0
        return int(until - time.time())

    def check_ip(self, ip: str) -> bool:
        settings = get_settings()
        now = time.time()
        hits = self._ip_hits[ip]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= settings.login_ip_max_per_minute:
            return False
        hits.append(now)
        return True

    def record_failure(self, username: str) -> None:
        settings = get_settings()
        now = time.time()
        fails = self._fails[username]
        while fails and now - fails[0] > settings.login_lock_minutes * 60:
            fails.popleft()
        fails.append(now)
        if len(fails) >= settings.login_max_failures:
            self._locked_until[username] = now + settings.login_lock_minutes * 60
            fails.clear()

    def reset(self, username: str) -> None:
        self._fails.pop(username, None)
        self._locked_until.pop(username, None)


limiter = LoginRateLimiter()
