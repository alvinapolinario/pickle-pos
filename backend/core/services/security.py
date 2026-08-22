"""Login lockout and request rate limits. Redis when available, memory otherwise."""

from __future__ import annotations

import time
from threading import Lock

from redis import Redis

from core.domain.exceptions import AuthenticationError


class _MemoryCounter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._values: dict[str, tuple[int, float]] = {}

    def incr(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        with self._lock:
            count, expires = self._values.get(key, (0, 0.0))
            if expires <= now:
                count = 0
            count += 1
            self._values[key] = (count, now + window_seconds)
            return count

    def get(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            count, expires = self._values.get(key, (0, 0.0))
            if expires <= now:
                return 0
            return count

    def ttl(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            _, expires = self._values.get(key, (0, 0.0))
            return max(int(expires - now), 0)

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)


_SHARED_MEMORY = _MemoryCounter()


def reset_security_counters() -> None:
    with _SHARED_MEMORY._lock:
        _SHARED_MEMORY._values.clear()


class RateLimiter:
    def __init__(self, redis_client: Redis | None = None) -> None:
        self.redis = redis_client
        self.memory = _SHARED_MEMORY

    def hit(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        count = self._incr(key, window_seconds)
        if count > limit:
            return False, self._ttl(key) or window_seconds
        return True, 0

    def get(self, key: str) -> int:
        if self.redis:
            try:
                return int(self.redis.get(key) or 0)
            except Exception:
                pass
        return self.memory.get(key)

    def _incr(self, key: str, window_seconds: int) -> int:
        if self.redis:
            try:
                count = int(self.redis.incr(key))
                if count == 1:
                    self.redis.expire(key, window_seconds)
                return count
            except Exception:
                pass
        return self.memory.incr(key, window_seconds)

    def _ttl(self, key: str) -> int:
        if self.redis:
            try:
                ttl = int(self.redis.ttl(key))
                return max(ttl, 0)
            except Exception:
                pass
        return self.memory.ttl(key)

    def reset(self, key: str) -> None:
        if self.redis:
            try:
                self.redis.delete(key)
            except Exception:
                pass
        self.memory.delete(key)


class LoginLockout:
    PREFIX = "login_fail:"

    def __init__(
        self,
        redis_client: Redis | None = None,
        *,
        max_attempts: int = 5,
        window_seconds: int = 900,
    ) -> None:
        self.limiter = RateLimiter(redis_client)
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds

    def _key(self, username: str) -> str:
        return f"{self.PREFIX}{username.strip().lower()}"

    def assert_unlocked(self, username: str) -> None:
        if self.limiter.get(self._key(username)) >= self.max_attempts:
            raise AuthenticationError("Account locked after too many failed logins. Try again later.")

    def record_failure(self, username: str) -> None:
        count = self.limiter._incr(self._key(username), self.window_seconds)
        if count >= self.max_attempts:
            raise AuthenticationError("Account locked after too many failed logins. Try again later.")

    def clear(self, username: str) -> None:
        self.limiter.reset(self._key(username))
