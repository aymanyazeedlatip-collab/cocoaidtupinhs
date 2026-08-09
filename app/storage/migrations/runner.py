from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.errors import MigrationError
from app.storage.migrations.base import Migration
from app.storage.migrations.versions import MIGRATIONS


@dataclass(frozen=True, slots=True)
class MigrationStatus:
    version: int
    name: str
    checksum: str
    state: str
    applied_at: str | None = None


class MigrationManager:
    def __init__(self, database_path: Path, migrations: tuple[Migration, ...] = MIGRATIONS) -> None:
        self.database_path = Path(database_path)
        self.migrations = tuple(sorted(migrations, key=lambda item: item.version))
        versions = [item.version for item in self.migrations]
        if len(versions) != len(set(versions)):
            raise ValueError("Migration versions must be unique")

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def _ensure_registry(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )

    def _applied(self, conn: sqlite3.Connection) -> dict[int, sqlite3.Row]:
        self._ensure_registry(conn)
        rows = conn.execute("SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version").fetchall()
        return {int(row["version"]): row for row in rows}

    def status(self) -> list[MigrationStatus]:
        conn = self._connect()
        try:
            applied = self._applied(conn)
            conn.commit()
            result: list[MigrationStatus] = []
            known_versions = {item.version for item in self.migrations}
            for migration in self.migrations:
                row = applied.get(migration.version)
                if row is None:
                    result.append(MigrationStatus(migration.version, migration.name, migration.checksum, "pending"))
                elif row["checksum"] != migration.checksum or row["name"] != migration.name:
                    result.append(MigrationStatus(migration.version, migration.name, migration.checksum, "checksum_mismatch", row["applied_at"]))
                else:
                    result.append(MigrationStatus(migration.version, migration.name, migration.checksum, "applied", row["applied_at"]))
            for version, row in applied.items():
                if version not in known_versions:
                    result.append(MigrationStatus(version, row["name"], row["checksum"], "unknown_applied", row["applied_at"]))
            return sorted(result, key=lambda item: item.version)
        finally:
            conn.close()

    def upgrade(self, target_version: int | None = None) -> list[int]:
        target = target_version if target_version is not None else (self.migrations[-1].version if self.migrations else 0)
        applied_versions: list[int] = []
        conn = self._connect()
        try:
            applied = self._applied(conn)
            conn.commit()
            for migration in self.migrations:
                if migration.version > target:
                    break
                row = applied.get(migration.version)
                if row is not None:
                    if row["checksum"] != migration.checksum or row["name"] != migration.name:
                        raise MigrationError(
                            f"Migration {migration.version} checksum mismatch",
                            details={"migration": migration.name},
                        )
                    continue
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    migration.up(conn)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
                        (migration.version, migration.name, migration.checksum, datetime.now(UTC).isoformat()),
                    )
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    raise MigrationError(
                        f"Failed to apply migration {migration.version}: {migration.name}",
                        details={"exception_type": type(exc).__name__},
                    ) from exc
                applied_versions.append(migration.version)
            return applied_versions
        finally:
            conn.close()

    def downgrade_one(self, *, allow_destructive: bool = False) -> int | None:
        conn = self._connect()
        try:
            applied = self._applied(conn)
            if not applied:
                return None
            version = max(applied)
            migration = next((item for item in self.migrations if item.version == version), None)
            if migration is None:
                raise MigrationError(f"Cannot roll back unknown migration version {version}")
            if migration.down is None:
                raise MigrationError(f"Migration {version} is irreversible")
            if migration.destructive_down and not allow_destructive:
                raise MigrationError(
                    f"Migration {version} rollback is destructive",
                    details={"required_flag": "allow_destructive"},
                )
            try:
                conn.commit()
                conn.execute("BEGIN IMMEDIATE")
                migration.down(conn)
                conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                conn.commit()
            except Exception as exc:
                conn.rollback()
                raise MigrationError(
                    f"Failed to roll back migration {version}: {migration.name}",
                    details={"exception_type": type(exc).__name__},
                ) from exc
            return version
        finally:
            conn.close()
