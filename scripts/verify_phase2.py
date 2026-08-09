from __future__ import annotations

from contextlib import closing

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_foundation.farmer_import import import_farmer_workbook
from app.data_foundation.repository import farmer_registry_summary, summary
from app.data_foundation.seeding import seed_reference_data
from app.storage.migrations import MigrationManager

EXPECTED_FARMER_ROWS = 17_798
REQUIRED_ARTIFACTS = [
    "docs/phase_2/ARCHITECTURE.md",
    "docs/phase_2/DATABASE_SCHEMA.md",
    "docs/phase_2/PCA_REFERENCE_CATALOG.md",
    "docs/phase_2/FARMER_IMPORT_PIPELINE.md",
    "docs/phase_2/PRIVACY_AND_PII.md",
    "docs/phase_2/WARNING_FIX.md",
    "docs/phase_2/USER_ACTIONS.md",
    "docs/phase_2/PHASE_2_STATUS.md",
    "docs/phase_2/TEST_REPORT.md",
    "docs/phase_2/RELEASE_NOTES.md",
    "manifests/phase2_reference_counts.json",
    "manifests/phase2_catalog_checksums.json",
    "manifests/phase2_migration_catalog.json",
    "manifests/phase2_source_registry.json",
    "baseline_snapshots/phase2_test_results.txt",
]


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 2 artifact: {relative}"
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "httpx2>=2.9.1,<3" in requirements
    assert "filterwarnings = error" in (ROOT / "pytest.ini").read_text(encoding="utf-8")
    test_result = (ROOT / "baseline_snapshots" / "phase2_test_results.txt").read_text(encoding="utf-8")
    assert "146 passed" in test_result
    assert "warning" not in test_result.lower()
    workbook = ROOT / "data_sources" / "raw" / "farmers" / "Farmers_Lists_Updated.xlsx"
    with tempfile.TemporaryDirectory(prefix="cocoaid-phase2-") as temp:
        database = Path(temp) / "phase2.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=2) == [1, 2]
        status = manager.status()
        assert [item.state for item in status[:2]] == ["applied", "applied"]
        seeded = seed_reference_data(database_path=database)
        seeded_again = seed_reference_data(database_path=database)
        assert seeded == seeded_again
        counts = summary(database_path=database)
        assert counts["source_documents"] == 16
        assert counts["coconut_varieties"] == 30
        assert counts["variety_parameters"] == 408
        assert counts["pest_profiles"] == 5
        assert counts["intercrop_candidates"] == 35
        assert counts["canopy_light_parameters"] == 81
        assert counts["fertilization_scenarios"] == 2

        dry = import_farmer_workbook(workbook, database_path=database, dry_run=True)
        assert dry.total_rows == EXPECTED_FARMER_ROWS
        assert dry.sheet_count == 12
        assert dry.import_run_id is None
        assert summary(database_path=database)["farmer_registry_records"] == 0

        imported = import_farmer_workbook(workbook, database_path=database)
        assert imported.total_rows == EXPECTED_FARMER_ROWS
        registry = farmer_registry_summary(database_path=database)
        assert registry["total_records"] == EXPECTED_FARMER_ROWS
        serialized_registry = json.dumps(registry, ensure_ascii=False).lower()
        assert "last_name" not in serialized_registry
        assert "santo niã" not in serialized_registry
        assert "santo niño" in serialized_registry
        with closing(sqlite3.connect(database)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM farmer_identities").fetchone()[0] == EXPECTED_FARMER_ROWS
            assert conn.execute("SELECT COUNT(*) FROM farmer_registry_staging").fetchone()[0] == EXPECTED_FARMER_ROWS
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

        reused = import_farmer_workbook(workbook, database_path=database)
        assert reused.reused_existing_run is True
        assert summary(database_path=database)["farmer_registry_records"] == EXPECTED_FARMER_ROWS
        print(json.dumps({"seed_counts": seeded, "import_summary": imported.as_dict(), "database_counts": summary(database_path=database)}, indent=2, ensure_ascii=False))
    print("PHASE 2 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
