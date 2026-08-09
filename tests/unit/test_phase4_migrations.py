from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from app.core.errors import MigrationError
from app.storage.migrations import MigrationManager


def _tables(path):
    with closing(sqlite3.connect(path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_phase4_migration_creates_production_and_economic_schema_idempotently(tmp_path):
    path = tmp_path / "phase4.sqlite3"
    manager = MigrationManager(path)
    assert manager.upgrade(target_version=4) == [1, 2, 3, 4]
    assert manager.upgrade(target_version=4) == []
    assert [item.state for item in manager.status()[:4]] == ["applied"] * 4
    assert [item.state for item in manager.status()[4:]] == ["pending"] * 6
    expected = {
        "production_feature_snapshots", "production_forecasts_v3", "production_product_estimates",
        "production_shadow_comparisons", "production_actuals", "intercrop_economic_profiles",
    }
    assert expected.issubset(_tables(path))
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_phase4_rollback_is_guarded_and_preserves_phase3_weather(tmp_path):
    path = tmp_path / "phase4.sqlite3"
    manager = MigrationManager(path)
    manager.upgrade(target_version=4)
    with pytest.raises(MigrationError, match="destructive"):
        manager.downgrade_one()
    assert manager.downgrade_one(allow_destructive=True) == 4
    names = _tables(path)
    assert "production_forecasts_v3" not in names
    assert "intercrop_economic_profiles" not in names
    assert "weather_model_runs" in names
    assert manager.upgrade(target_version=4) == [4]
