from __future__ import annotations

from contextlib import closing

import sqlite3

import pytest

from app.core.errors import MigrationError
from app.storage.migrations import MigrationManager


def _tables(path):
    with closing(sqlite3.connect(path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_phase2_migration_creates_normalized_schema_and_is_idempotent(tmp_path):
    path = tmp_path / "phase2.sqlite3"
    manager = MigrationManager(path)
    assert manager.upgrade(target_version=2) == [1, 2]
    assert manager.upgrade(target_version=2) == []
    assert [item.state for item in manager.status()] == ["applied", "applied"] + ["pending"] * 8
    expected = {
        "source_documents", "coconut_varieties", "variety_parameters", "pest_profiles",
        "pest_evidence_rules", "pest_management_actions", "intercrop_candidates",
        "canopy_light_parameters", "fertilization_scenarios", "farmer_import_runs",
        "farmer_registry_staging", "farmer_identities", "farmer_registry",
        "farmer_quality_flags", "system_metadata",
    }
    assert expected.issubset(_tables(path))
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_phase2_rollback_is_guarded_and_preserves_legacy_schema(tmp_path):
    path = tmp_path / "phase2.sqlite3"
    manager = MigrationManager(path)
    manager.upgrade(target_version=2)
    with pytest.raises(MigrationError, match="destructive"):
        manager.downgrade_one()
    assert manager.downgrade_one(allow_destructive=True) == 2
    names = _tables(path)
    assert "source_documents" not in names
    assert {"farms", "analyses", "reports", "saved_forecasts"}.issubset(names)
    assert [item.state for item in manager.status()] == ["applied"] + ["pending"] * 9
    assert manager.upgrade(target_version=2) == [2]


def test_phase2_upgrade_preserves_existing_legacy_records(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    manager = MigrationManager(path)
    manager.upgrade(target_version=1)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "INSERT INTO farms(id, payload, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("legacy-farm", "{}", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()
    assert manager.upgrade(target_version=2) == [2]
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT id FROM farms").fetchone()[0] == "legacy-farm"
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
