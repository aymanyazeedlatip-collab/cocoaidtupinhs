from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Callable

MigrationCallable = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    up: MigrationCallable
    down: MigrationCallable | None
    fingerprint: str
    destructive_down: bool = False

    @property
    def checksum(self) -> str:
        material = f"{self.version}:{self.name}:{self.fingerprint}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()
