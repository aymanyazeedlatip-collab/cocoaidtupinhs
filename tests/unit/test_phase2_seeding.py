from __future__ import annotations

from app.data_foundation import repository
from app.data_foundation.seeding import seed_reference_data
from app.storage.migrations import MigrationManager


EXPECTED = {
    "source_documents": 16,
    "coconut_varieties": 30,
    "variety_parameters": 408,
    "pest_profiles": 5,
    "pest_evidence_rules": 17,
    "pest_management_actions": 14,
    "intercrop_candidates": 35,
    "canopy_light_parameters": 81,
    "fertilization_scenarios": 2,
}


def test_reference_seed_is_checksum_verified_and_idempotent(tmp_path):
    database = tmp_path / "phase2.sqlite3"
    MigrationManager(database).upgrade(target_version=2)
    first = seed_reference_data(database_path=database)
    second = seed_reference_data(database_path=database)
    assert first == EXPECTED
    assert second == EXPECTED
    counts = repository.summary(database_path=database)
    for key, value in EXPECTED.items():
        assert counts[key] == value


def test_public_source_catalog_excludes_farmer_pii_document(tmp_path):
    database = tmp_path / "phase2.sqlite3"
    MigrationManager(database).upgrade(target_version=2)
    seed_reference_data(database_path=database)
    public = repository.list_source_documents(database_path=database)
    internal = repository.list_source_documents(include_restricted=True, database_path=database)
    assert len(public) == 14
    assert len(internal) == 16
    assert all(item["access_class"] != "restricted_pii" for item in public)
    assert any(item["access_class"] == "restricted_pii" for item in internal)
