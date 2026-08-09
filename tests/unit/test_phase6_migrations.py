from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from app.core.errors import MigrationError
from app.storage.migrations import MigrationManager


TABLES = {
    "pest_observations_v3",
    "pest_assessment_runs",
    "pest_assessments_v3",
    "pest_assessment_contributions",
    "pest_assessment_actions",
}


def test_phase6_migration_creates_schema_idempotently(tmp_path):
    path = tmp_path / "phase6.sqlite3"
    manager = MigrationManager(path)
    assert manager.upgrade(target_version=6) == [1, 2, 3, 4, 5, 6]
    assert manager.upgrade(target_version=6) == []
    with closing(sqlite3.connect(path)) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert TABLES <= tables
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_phase6_rollback_is_guarded(tmp_path):
    path = tmp_path / "phase6.sqlite3"
    manager = MigrationManager(path)
    manager.upgrade(target_version=6)
    with pytest.raises(MigrationError):
        manager.downgrade_one()
    assert manager.downgrade_one(allow_destructive=True) == 6
    with closing(sqlite3.connect(path)) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not (TABLES & tables)
        assert "bayesian_posteriors" in tables
    assert manager.upgrade(target_version=6) == [6]
