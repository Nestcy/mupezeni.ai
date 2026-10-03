from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


class AnalyticsCache:
    """Lightweight application-level cache for analytics queries."""

    def __init__(self):
        self._cache: dict[str, tuple[datetime, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._cache.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < datetime.utcnow():
            self._cache.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> Any:
        self._cache[key] = (datetime.utcnow() + timedelta(seconds=ttl_seconds), value)
        return value


__all__ = ["AnalyticsCache"]
