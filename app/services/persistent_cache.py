from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from pathlib import Path
from threading import RLock
from typing import Any

from app.core.config import settings


class PersistentJsonCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, key: str) -> Path:
        return self.directory / f"{hashlib.sha256(key.encode()).hexdigest()}.json.gz"

    def get(self, key: str, max_age_seconds: int) -> dict[str, Any] | None:
        path = self._path(key)
        try:
            if time.time() - path.stat().st_mtime > max_age_seconds:
                return None
            with self._lock, gzip.open(path, "rt", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else None
        except (OSError, ValueError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        path = self._path(key)
        temp = path.with_suffix(".tmp")
        try:
            with self._lock, gzip.open(temp, "wt", encoding="utf-8") as handle:
                json.dump(value, handle, separators=(",", ":"), allow_nan=False)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


persistent_cache = PersistentJsonCache(settings.cache_dir)
