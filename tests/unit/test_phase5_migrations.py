from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from app.core.errors import MigrationError
from app.storage.migrations import MigrationManager


def _tables(path):
    with closing(sqlite3.connect(path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_phase5_migration_creates_bayesian_schema_idempotently(tmp_path):
    path = tmp_path / "phase5.sqlite3"
    manager = MigrationManager(path)
    assert manager.upgrade(target_version=5) == [1, 2, 3, 4, 5]
    assert manager.upgrade(target_version=5) == []
    assert [item.state for item in manager.status()] == ["applied"] * 5 + ["pending"] * 5
    expected = {
        "bayesian_evidence_observations", "bayesian_runs", "bayesian_posteriors",
        "bayesian_parameter_posteriors", "bayesian_evidence_assimilation",
    }
    assert expected.issubset(_tables(path))
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_phase5_rollback_is_guarded_and_preserves_phase4_production(tmp_path):
    path = tmp_path / "phase5.sqlite3"
    manager = MigrationManager(path)
    manager.upgrade(target_version=5)
    with pytest.raises(MigrationError, match="destructive"):
        manager.downgrade_one()
    assert manager.downgrade_one(allow_destructive=True) == 5
    names = _tables(path)
    assert "bayesian_posteriors" not in names
    assert "production_forecasts_v3" in names
    assert manager.upgrade(target_version=5) == [5]
