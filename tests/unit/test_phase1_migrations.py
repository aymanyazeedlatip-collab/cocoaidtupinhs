from __future__ import annotations

from contextlib import closing

import sqlite3

import pytest

from app.core.errors import MigrationError
from app.storage.migrations import MigrationManager


def table_names(path):
    with closing(sqlite3.connect(path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def test_migration_framework_upgrade_is_idempotent_and_records_checksum(tmp_path):
    path = tmp_path / "phase1.sqlite3"
    manager = MigrationManager(path)
    assert manager.status()[0].state == "pending"
    assert manager.upgrade(target_version=1) == [1]
    assert manager.upgrade(target_version=1) == []
    status = manager.status()[0]
    assert status.state == "applied"
    assert len(status.checksum) == 64
    assert {"farms", "analyses", "reports", "saved_forecasts", "schema_migrations"}.issubset(table_names(path))


def test_destructive_migration_rollback_requires_explicit_permission(tmp_path):
    path = tmp_path / "phase1.sqlite3"
    manager = MigrationManager(path)
    manager.upgrade(target_version=1)
    with pytest.raises(MigrationError, match="destructive"):
        manager.downgrade_one()
    assert manager.downgrade_one(allow_destructive=True) == 1
    assert "farms" not in table_names(path)
    assert manager.status()[0].state == "pending"
    assert manager.upgrade(target_version=1) == [1]


def test_migration_upgrades_older_report_schema_without_deleting_records(tmp_path):
    path = tmp_path / "older.sqlite3"
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript(
            """
            CREATE TABLE reports (id TEXT PRIMARY KEY, analysis_id TEXT, filepath TEXT NOT NULL, created_at TEXT NOT NULL);
            INSERT INTO reports (id, analysis_id, filepath, created_at) VALUES ('r1', NULL, 'report.pdf', '2026-01-01T00:00:00+00:00');
            """
        )
    MigrationManager(path).upgrade()
    with closing(sqlite3.connect(path)) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(reports)").fetchall()}
        row = conn.execute("SELECT id, report_type FROM reports WHERE id='r1'").fetchone()
    assert "report_type" in columns
    assert row == ("r1", "pdf")
