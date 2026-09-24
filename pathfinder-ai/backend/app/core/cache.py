"""Tiny cache facade: Redis when configured, in-process TTL dict otherwise."""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from app.core.config import get_settings

log = logging.getLogger("pathfinder.cache")


class _MemoryBackend:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, value = item
            if expires and expires < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            self._data[key] = (time.time() + ttl if ttl else 0, value)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            for k in [k for k in self._data if k.startswith(prefix)]:
                self._data.pop(k, None)

    def incr_window(self, key: str, window: int) -> int:
        with self._lock:
            now = time.time()
            expires, value = self._data.get(key, (now + window, "0"))
            if expires < now:
                expires, value = now + window, "0"
            count = int(value) + 1
            self._data[key] = (expires, str(count))
            return count


class Cache:
    def __init__(self) -> None:
        self._memory = _MemoryBackend()
        self._redis = None
        url = get_settings().redis_url
        if url:
            try:
                import redis

                client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
                client.ping()
                self._redis = client
            except Exception as exc:  # pragma: no cover - depends on infra
                log.warning("Redis unavailable (%s); using in-memory cache", exc)

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    def get_json(self, key: str) -> Any | None:
        try:
            raw = self._redis.get(key) if self._redis else self._memory.get(key)
        except Exception:
            raw = self._memory.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, value: Any, ttl: int = 300) -> None:
        raw = json.dumps(value, default=str)
        try:
            if self._redis:
                self._redis.set(key, raw, ex=ttl)
                return
        except Exception:
            pass
        self._memory.set(key, raw, ttl)

    def invalidate(self, prefix: str) -> None:
        try:
            if self._redis:
                for k in self._redis.scan_iter(f"{prefix}*"):
                    self._redis.delete(k)
        except Exception:
            pass
        self._memory.delete_prefix(prefix)

    def hit(self, key: str, window: int = 60) -> int:
        """Increment a fixed-window counter and return the current count."""
        try:
            if self._redis:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, window, nx=True)
                count, _ = pipe.execute()
                return int(count)
        except Exception:
            pass
        return self._memory.incr_window(key, window)


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
