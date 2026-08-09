from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    stored_at: float


class TTLCache:
    def __init__(self, max_items: int = 512) -> None:
        self.max_items = max_items
        self._items: dict[str, CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if not item or item.expires_at <= now:
                return None
            return item.value

    def get_stale(self, key: str, max_stale_seconds: int) -> Any | None:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            if now <= item.expires_at + max_stale_seconds:
                return item.value
            self._items.pop(key, None)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        now = time.time()
        with self._lock:
            if len(self._items) >= self.max_items and key not in self._items:
                oldest = min(self._items, key=lambda k: self._items[k].stored_at)
                self._items.pop(oldest, None)
            self._items[key] = CacheEntry(value, now + ttl_seconds, now)

    def stats(self) -> dict[str, int]:
        now = time.time()
        with self._lock:
            fresh = sum(1 for v in self._items.values() if v.expires_at > now)
            return {"items": len(self._items), "fresh_items": fresh, "stale_items": len(self._items) - fresh, "capacity": self.max_items}


cache = TTLCache()
