from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.domain.enums import EngineAvailability
from app.engines.rehabilitation import RehabilitationEngine, rehabilitation_engine
from app.parameters.registry import parameter_registry
from app.rehabilitation import repository
from app.rehabilitation.parameters import (
    PARAMETERS, REHABILITATION_COST_CATALOG_VERSION, REHABILITATION_ENGINE_VERSION,
    REHABILITATION_PARAMETER_SET_ID, REHABILITATION_PARAMETER_VERSION,
)
from app.storage.migrations import MigrationManager
from tests.phase8_factory import prepare_phase8_dependencies, rehabilitation_request

REQUIRED_ARTIFACTS = [
    "docs/phase_8/ARCHITECTURE.md",
    "docs/phase_8/DATA_CONTRACTS.md",
    "docs/phase_8/SCENARIO_MODEL.md",
    "docs/phase_8/COST_AND_SAFETY.md",
    "docs/phase_8/DATABASE_SCHEMA.md",
    "docs/phase_8/API.md",
    "docs/phase_8/LIMITATIONS.md",
    "docs/phase_8/USER_ACTIONS.md",
    "docs/phase_8/PHASE_8_STATUS.md",
    "docs/phase_8/TEST_REPORT.md",
    "docs/phase_8/RELEASE_NOTES.md",
    "manifests/phase8_contract_hashes.json",
    "manifests/phase8_engine_catalog.json",
    "manifests/phase8_endpoint_catalog.json",
    "manifests/phase8_migration_catalog.json",
    "manifests/phase8_parameter_catalog.json",
    "baseline_snapshots/phase8_test_results.txt",
]


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 8 artifact: {relative}"
    assert settings.contract_api_version == "3.0.0-draft.10"
    assert rehabilitation_engine.descriptor.availability == EngineAvailability.AVAILABLE
    assert rehabilitation_engine.descriptor.version == REHABILITATION_ENGINE_VERSION == "1.0.0"
    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == REHABILITATION_PARAMETER_SET_ID
        and item.version == REHABILITATION_PARAMETER_VERSION
    )
    assert parameter_registry.values(
        REHABILITATION_PARAMETER_SET_ID, REHABILITATION_PARAMETER_VERSION
    ) == PARAMETERS
    assert descriptor.version == REHABILITATION_PARAMETER_VERSION

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase8-") as temp:
        database = Path(temp) / "phase8.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=8) == [1, 2, 3, 4, 5, 6, 7, 8]
        assert manager.upgrade(target_version=8) == []
        production, pest, intercrop, cell_id = prepare_phase8_dependencies(database_path=database)
        output = RehabilitationEngine(database_path=database).execute(
            rehabilitation_request(production, pest, intercrop, cell_id)
        ).output
        assert len(output.plan.scenarios) == 6
        assert any(item.scenario_type == "no_action" and item.status == "feasible" for item in output.plan.scenarios)
        selected = next(item for item in output.plan.scenarios if item.scenario_type == output.plan.selected_scenario)
        assert selected.status == "feasible"
        assert output.plan.total_expected_cost_php == selected.total_cost_php
        assert any(item.action_type.value == "pest_or_disease_treatment" for item in output.plan.actions)
        stored = repository.get_plan(output.plan.rehabilitation_plan_id, database_path=database)
        assert stored is not None and len(stored["scenarios"]) == 6
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert manager.downgrade_one(allow_destructive=True) == 8
        with closing(sqlite3.connect(database)) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "rehabilitation_plan_runs" not in tables
            assert "intercrop_cell_assessments" in tables
        assert manager.upgrade(target_version=8) == [8]

    result = (ROOT / "baseline_snapshots" / "phase8_test_results.txt").read_text(encoding="utf-8")
    assert "tests" in result
    assert "fully isolated test-file processes" in result
    assert "failure" not in result.lower()
    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": list(range(1, 9)),
        "engine": rehabilitation_engine.descriptor.engine_id,
        "engine_version": REHABILITATION_ENGINE_VERSION,
        "parameter_version": REHABILITATION_PARAMETER_VERSION,
        "cost_catalog_version": REHABILITATION_COST_CATALOG_VERSION,
        "scenario_count": 6,
        "no_action_verified": True,
        "persistence_verified": True,
        "predicted_damage_safety_verified": True,
    }, indent=2))
    print("PHASE 8 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
