from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.data_foundation.seeding import seed_reference_data
from app.domain.enums import EngineAvailability
from app.domain.intercropping import IntercropAssessmentRequest, IntercropCellContext
from app.engines.intercropping import IntercroppingEngine, intercropping_engine
from app.intercropping import repository
from app.intercropping.parameters import (
    INTERCROP_ENGINE_VERSION,
    INTERCROP_PARAMETER_SET_ID,
    INTERCROP_PARAMETER_VERSION,
    INTERCROP_REQUIREMENT_PROFILE_VERSION,
    PARAMETERS,
)
from app.parameters.registry import parameter_registry
from app.storage.migrations import MigrationManager
from tests.phase5_factory import prepare_phase5_production

REQUIRED_ARTIFACTS = [
    "docs/phase_7/ARCHITECTURE.md",
    "docs/phase_7/DATA_CONTRACTS.md",
    "docs/phase_7/SCORING_MODEL.md",
    "docs/phase_7/DATABASE_SCHEMA.md",
    "docs/phase_7/API.md",
    "docs/phase_7/LIMITATIONS.md",
    "docs/phase_7/USER_ACTIONS.md",
    "docs/phase_7/PHASE_7_STATUS.md",
    "docs/phase_7/RELEASE_NOTES.md",
    "docs/phase_7/TEST_REPORT.md",
    "manifests/phase7_contract_hashes.json",
    "manifests/phase7_engine_catalog.json",
    "manifests/phase7_endpoint_catalog.json",
    "manifests/phase7_migration_catalog.json",
    "manifests/phase7_parameter_catalog.json",
    "manifests/phase7_requirement_catalog.json",
    "baseline_snapshots/phase7_test_results.txt",
]


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 7 artifact: {relative}"

    assert settings.contract_api_version == "3.0.0-draft.10"
    assert intercropping_engine.descriptor.availability == EngineAvailability.AVAILABLE
    assert intercropping_engine.descriptor.version == INTERCROP_ENGINE_VERSION == "1.0.0"

    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == INTERCROP_PARAMETER_SET_ID
        and item.version == INTERCROP_PARAMETER_VERSION
    )
    assert descriptor.version == INTERCROP_PARAMETER_VERSION
    assert parameter_registry.values(
        INTERCROP_PARAMETER_SET_ID, INTERCROP_PARAMETER_VERSION
    ) == PARAMETERS

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase7-") as temp:
        database = Path(temp) / "phase7.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=7) == [1, 2, 3, 4, 5, 6, 7]
        assert manager.upgrade(target_version=7) == []
        counts = seed_reference_data(database_path=database)
        assert counts["intercrop_candidates"] == 35
        assert counts["canopy_light_parameters"] == 81
        assert counts["intercrop_requirement_profiles"] == 35

        production = prepare_phase5_production(database_path=database)
        request = IntercropAssessmentRequest(
            farm_id=production.forecast.farm_id,
            production_forecast_id=production.forecast.production_forecast_id,
            assessed_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
            candidate_ids=["cacao", "coffee", "sugarcane"],
            cells=[IntercropCellContext(
                label="Verification cell",
                area_hectares=1.0,
                palm_age_years=40,
                spacing_x_m=8.0,
                spacing_y_m=8.0,
                canopy_design="square",
                canopy_density_index=0.65,
                slope_degrees=4.0,
                drainage_index=0.65,
                soil_ph=6.1,
                soil_moisture_index=0.58,
                nitrogen_index=0.65,
                available_space_fraction=0.70,
                management_feasibility=0.72,
                market_access_index=0.60,
            )],
            farm_data_version="phase7-verification-farm-1",
        )
        output = IntercroppingEngine(database_path=database).execute(request).output
        assert output.requirement_profile_version == INTERCROP_REQUIREMENT_PROFILE_VERSION
        assert output.summary.total_assessment_count == 3
        by_id = {item.candidate.candidate_id: item for item in output.assessments}
        assert by_id["cacao"].economic_potential.status == "available"
        assert by_id["coffee"].economic_potential.status == "available"
        assert by_id["sugarcane"].hard_constraint_passed is False
        assert by_id["sugarcane"].suitability_score <= 40
        assert abs(by_id["cacao"].canopy_light.transmitted_light_fraction - 0.37) < 1e-9

        stored = repository.get_assessment(
            by_id["cacao"].assessment_id, database_path=database
        )
        assert stored is not None
        assert len(stored["components"]) == 9

        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

        assert manager.downgrade_one(allow_destructive=True) == 7
        with closing(sqlite3.connect(database)) as conn:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert "intercrop_cell_assessments" not in tables
            assert "pest_assessments_v3" in tables
        assert manager.upgrade(target_version=7) == [7]

    result = (ROOT / "baseline_snapshots" / "phase7_test_results.txt").read_text(
        encoding="utf-8"
    )
    assert "tests" in result
    assert "fully isolated test-file processes" in result
    assert "warning" not in result.lower()
    assert "failure" not in result.lower()

    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": [1, 2, 3, 4, 5, 6, 7],
        "engine": intercropping_engine.descriptor.engine_id,
        "engine_version": INTERCROP_ENGINE_VERSION,
        "parameter_version": INTERCROP_PARAMETER_VERSION,
        "requirement_profile_version": INTERCROP_REQUIREMENT_PROFILE_VERSION,
        "candidate_count": 35,
        "canopy_rows": 81,
        "economic_candidates": ["cacao", "coffee"],
        "hard_constraint_cap_verified": True,
        "persistence_verified": True,
    }, indent=2))
    print("PHASE 7 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
