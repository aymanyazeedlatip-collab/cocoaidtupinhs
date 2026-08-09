from __future__ import annotations

import sqlite3
from contextlib import closing

from app.data_foundation.seeding import seed_reference_data
from app.storage.migrations import MigrationManager


def test_phase7_migration_seed_integrity_and_rollback(tmp_path):
    database = tmp_path / "phase7.sqlite3"
    manager = MigrationManager(database)
    assert manager.upgrade(target_version=7) == [1, 2, 3, 4, 5, 6, 7]
    assert manager.upgrade(target_version=7) == []
    counts = seed_reference_data(database_path=database)
    assert counts["intercrop_requirement_profiles"] == 35
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("SELECT COUNT(*) FROM intercrop_requirement_profiles").fetchone()[0] == 35
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert manager.downgrade_one(allow_destructive=True) == 7
    with closing(sqlite3.connect(database)) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "intercrop_cell_assessments" not in tables
        assert "pest_assessments_v3" in tables
    assert manager.upgrade(target_version=7) == [7]
