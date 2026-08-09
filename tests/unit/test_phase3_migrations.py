from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from app.core.errors import MigrationError
from app.storage.migrations import MigrationManager


def _tables(path):
    with closing(sqlite3.connect(path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_phase3_migration_creates_weather_schema_and_is_idempotent(tmp_path):
    path = tmp_path / "phase3.sqlite3"
    manager = MigrationManager(path)
    assert manager.upgrade(target_version=3) == [1, 2, 3]
    assert manager.upgrade(target_version=3) == []
    assert [item.state for item in manager.status()] == ["applied"] * 3 + ["pending"] * 7
    assert {
        "weather_model_runs", "weather_values", "weather_feature_sets", "weather_features",
    }.issubset(_tables(path))
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_phase3_rollback_is_guarded_and_preserves_phase2_data(tmp_path):
    path = tmp_path / "phase3.sqlite3"
    manager = MigrationManager(path)
    manager.upgrade(target_version=3)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "INSERT INTO system_metadata(key, value, updated_at) VALUES (?,?,?)",
            ("phase2-test", "preserved", "2026-08-03T00:00:00+00:00"),
        )
        conn.commit()
    with pytest.raises(MigrationError, match="destructive"):
        manager.downgrade_one()
    assert manager.downgrade_one(allow_destructive=True) == 3
    names = _tables(path)
    assert "weather_model_runs" not in names
    assert "source_documents" in names
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT value FROM system_metadata WHERE key='phase2-test'").fetchone()[0] == "preserved"
    assert manager.upgrade(target_version=3) == [3]
