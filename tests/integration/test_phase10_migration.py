from __future__ import annotations

import sqlite3
from contextlib import closing

from app.storage.migrations import MigrationManager


def test_phase10_migration_integrity_and_rollback(tmp_path):
    database = tmp_path / "phase10.sqlite3"
    manager = MigrationManager(database)
    assert manager.upgrade(target_version=10) == list(range(1, 11))
    assert manager.upgrade(target_version=10) == []
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "coco_pilot_runs" in tables
        assert "formal_report_runs" in tables
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert manager.downgrade_one(allow_destructive=True) == 10
    with closing(sqlite3.connect(database)) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "coco_pilot_runs" not in tables
        assert "decision_support_runs" in tables
    assert manager.upgrade(target_version=10) == [10]
