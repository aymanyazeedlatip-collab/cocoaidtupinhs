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
from app.decision_support import repository
from app.decision_support.parameters import (
    DECISION_SUPPORT_ENGINE_VERSION, DECISION_SUPPORT_PARAMETER_SET_ID,
    DECISION_SUPPORT_PARAMETER_VERSION, DEPENDENCY_GRAPH_VERSION, PARAMETERS,
)
from app.domain.enums import EngineAvailability
from app.engines.decision_support import DecisionSupportEngine, decision_support_engine
from app.parameters.registry import parameter_registry
from app.storage.migrations import MigrationManager
from tests.phase9_factory import decision_request, prepare_phase9_records

REQUIRED_ARTIFACTS = [
    "docs/phase_9/ARCHITECTURE.md",
    "docs/phase_9/DATA_CONTRACTS.md",
    "docs/phase_9/DEPENDENCY_AND_FAILURE_MODEL.md",
    "docs/phase_9/RECOMMENDATION_TRACEABILITY.md",
    "docs/phase_9/DATABASE_SCHEMA.md",
    "docs/phase_9/API.md",
    "docs/phase_9/LIMITATIONS.md",
    "docs/phase_9/USER_ACTIONS.md",
    "docs/phase_9/PHASE_9_STATUS.md",
    "docs/phase_9/TEST_REPORT.md",
    "docs/phase_9/RELEASE_NOTES.md",
    "manifests/phase9_contract_hashes.json",
    "manifests/phase9_engine_catalog.json",
    "manifests/phase9_endpoint_catalog.json",
    "manifests/phase9_migration_catalog.json",
    "manifests/phase9_parameter_catalog.json",
    "run_phase9_workflow.bat",
    "scripts/run_phase9_workflow.py",
    "baseline_snapshots/phase9_test_results.txt",
]


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 9 artifact: {relative}"
    assert settings.contract_api_version == "3.0.0-draft.10"
    assert decision_support_engine.descriptor.availability == EngineAvailability.AVAILABLE
    assert decision_support_engine.descriptor.version == DECISION_SUPPORT_ENGINE_VERSION == "1.0.0"
    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == DECISION_SUPPORT_PARAMETER_SET_ID
        and item.version == DECISION_SUPPORT_PARAMETER_VERSION
    )
    assert parameter_registry.values(DECISION_SUPPORT_PARAMETER_SET_ID, DECISION_SUPPORT_PARAMETER_VERSION) == PARAMETERS
    assert descriptor.version == DECISION_SUPPORT_PARAMETER_VERSION

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase9-") as temp:
        database = Path(temp) / "phase9.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=9) == list(range(1, 10))
        assert manager.upgrade(target_version=9) == []
        production, posterior, pest, intercrop, rehabilitation = prepare_phase9_records(database_path=database)
        output = DecisionSupportEngine(database_path=database).execute(
            decision_request(production, posterior, pest, intercrop, rehabilitation)
        ).output
        assert output.record.status == "completed"
        assert output.summary.succeeded_components == 5
        assert output.summary.data_completeness == 1
        assert output.record.recommendations
        assert all(item.evidence for item in output.record.recommendations)
        stored = repository.get_run(output.record.analysis_run_id, database_path=database)
        assert stored is not None and len(stored["component_results"]) == 5
        partial = DecisionSupportEngine(database_path=database).execute(
            decision_request(production, posterior, pest, intercrop, rehabilitation, posterior_id=None)
        ).output
        assert partial.record.status == "partially_completed"
        assert partial.summary.data_completeness == 0.8
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert manager.downgrade_one(allow_destructive=True) == 9
        with closing(sqlite3.connect(database)) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "decision_support_runs" not in tables
            assert "rehabilitation_plan_runs" in tables
        assert manager.upgrade(target_version=9) == [9]

    result = (ROOT / "baseline_snapshots" / "phase9_test_results.txt").read_text(encoding="utf-8")
    assert "tests" in result
    assert "79 test files" in result
    assert "failure" not in result.lower()
    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": list(range(1, 10)),
        "engine": decision_support_engine.descriptor.engine_id,
        "engine_version": DECISION_SUPPORT_ENGINE_VERSION,
        "parameter_version": DECISION_SUPPORT_PARAMETER_VERSION,
        "dependency_graph_version": DEPENDENCY_GRAPH_VERSION,
        "complete_run_verified": True,
        "partial_run_verified": True,
        "persistence_verified": True,
        "traceability_verified": True,
    }, indent=2))
    print("PHASE 9 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
