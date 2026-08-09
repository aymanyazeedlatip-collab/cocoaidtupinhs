from __future__ import annotations

import sqlite3
from contextlib import closing

from app.storage.migrations import MigrationManager


def test_phase9_migration_integrity_and_rollback(tmp_path):
    database = tmp_path / "phase9.sqlite3"
    manager = MigrationManager(database)
    assert manager.upgrade(target_version=9) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert manager.upgrade(target_version=9) == []
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "decision_support_runs" in tables
        assert "decision_support_recommendations" in tables
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert manager.downgrade_one(allow_destructive=True) == 9
    with closing(sqlite3.connect(database)) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "decision_support_runs" not in tables
        assert "rehabilitation_plan_runs" in tables
    assert manager.upgrade(target_version=9) == [9]
