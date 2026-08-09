from __future__ import annotations

from app.core.config import settings
from app.data_foundation import repository
from app.data_foundation import seeding
from app.storage.migrations import MigrationManager


def test_production_default_seeding_does_not_require_raw_source_files(monkeypatch, tmp_path):
    """Render/GitHub deployments intentionally exclude data_sources/raw."""
    database = tmp_path / "production_seed.sqlite3"
    MigrationManager(database).upgrade(target_version=2)
    monkeypatch.setattr(settings, "environment", "production")

    def fail_if_raw_file_is_hashed(_path):
        raise AssertionError("production catalog seeding must not hash data_sources/raw")

    monkeypatch.setattr(seeding, "_sha256", fail_if_raw_file_is_hashed)
    counts = seeding.seed_reference_data(database_path=database)

    assert counts["source_documents"] == 16
    assert counts["coconut_varieties"] == 30
    assert counts["intercrop_candidates"] == 35
    assert repository.summary(database_path=database)["source_documents"] == 16


def test_explicit_reference_file_verification_remains_available(monkeypatch, tmp_path):
    database = tmp_path / "strict_seed.sqlite3"
    MigrationManager(database).upgrade(target_version=2)
    monkeypatch.setattr(settings, "environment", "production")

    calls = {"count": 0}
    original = seeding._sha256

    def counting_sha(path):
        calls["count"] += 1
        return original(path)

    monkeypatch.setattr(seeding, "_sha256", counting_sha)
    seeding.seed_reference_data(database_path=database, verify_files=True)
    assert calls["count"] == 16
