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

from app.bayesian import BAYESIAN_PARAMETER_VERSION, repository
from app.core.config import settings
from app.domain.bayesian import BayesianEvidenceObservation
from app.domain.enums import EngineAvailability
from app.engines.bayesian import BayesianEngine, bayesian_engine
from app.parameters.registry import parameter_registry
from app.production import repository as production_repository
from app.storage.migrations import MigrationManager
from tests.phase5_factory import bayesian_request, prepare_phase5_production

REQUIRED_ARTIFACTS = [
    "docs/phase_5/ARCHITECTURE.md",
    "docs/phase_5/DATA_CONTRACTS.md",
    "docs/phase_5/PARTICLE_FILTER.md",
    "docs/phase_5/DATABASE_SCHEMA.md",
    "docs/phase_5/API.md",
    "docs/phase_5/LIMITATIONS.md",
    "docs/phase_5/TEST_REPORT.md",
    "docs/phase_5/USER_ACTIONS.md",
    "docs/phase_5/PHASE_5_STATUS.md",
    "docs/phase_5/RELEASE_NOTES.md",
    "manifests/phase5_contract_hashes.json",
    "manifests/phase5_engine_catalog.json",
    "manifests/phase5_endpoint_catalog.json",
    "manifests/phase5_migration_catalog.json",
    "manifests/phase5_parameter_catalog.json",
    "baseline_snapshots/phase5_test_results.txt",
]


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 5 artifact: {relative}"
    assert settings.contract_api_version == "3.0.0-draft.10"
    assert bayesian_engine.descriptor.availability == EngineAvailability.AVAILABLE
    assert bayesian_engine.descriptor.version == "1.0.0"
    assert bayesian_engine.descriptor.deterministic_with_seed is True
    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == "v3.bayesian_farm_state"
    )
    assert descriptor.version == BAYESIAN_PARAMETER_VERSION
    values = parameter_registry.values("v3.bayesian_farm_state", BAYESIAN_PARAMETER_VERSION)
    assert values["maximum_particle_count"] == 5000
    assert values["evidence_reliability"]["predicted"] == 0.0
    assert values["evidence_reliability"]["expert_confirmed"] == 1.0

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase5-") as temp:
        database = Path(temp) / "phase5.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=5) == [1, 2, 3, 4, 5]
        assert manager.upgrade(target_version=5) == []
        production = prepare_phase5_production(database_path=database)
        forecast = production.forecast
        predicted = BayesianEvidenceObservation(
            farm_id=forecast.farm_id,
            production_forecast_id=forecast.production_forecast_id,
            evidence_type="storm_damage",
            evidence_status="predicted",
            observed_at=datetime(2026, 8, 4, tzinfo=UTC),
            value=0.80,
            unit="fraction",
            source_label="forecast traceability test",
        )
        confirmed = BayesianEvidenceObservation(
            farm_id=forecast.farm_id,
            production_forecast_id=forecast.production_forecast_id,
            evidence_type="pest_prevalence",
            evidence_status="field_confirmed",
            observed_at=datetime(2026, 8, 5, tzinfo=UTC),
            value=0.35,
            unit="fraction",
            source_label="field verification test",
        )
        repository.save_observation(predicted, database_path=database)
        repository.save_observation(confirmed, database_path=database)
        engine = BayesianEngine(database_path=database)
        request = bayesian_request(
            forecast.production_forecast_id,
            evidence_observation_ids=[predicted.observation_id, confirmed.observation_id],
            random_seed=445566,
            particle_count=400,
        )
        first = engine.execute(request).output
        repeat = engine.execute(request).output
        assert first.posterior.production_distribution == repeat.posterior.production_distribution
        assert first.posterior.state == repeat.posterior.state
        assert first.posterior.state.total_palms == request.initial_state.total_palms
        assert first.diagnostics.palm_count_conserved is True
        assert first.diagnostics.evidence_count_requested == 2
        assert first.diagnostics.evidence_count_used == 1
        assert [item.used_for_update for item in first.evidence_results] == [False, True]
        assert 0 <= first.posterior.probability_of_decline <= 1
        assert 0 <= first.posterior.probability_of_recovery <= 1
        assert len(first.posterior.parameters) == 8
        assert len(first.posterior.state_intervals) == 9

        sequential = engine.execute(bayesian_request(
            forecast.production_forecast_id,
            initial_state=None,
            prior_posterior_id=first.posterior.posterior_id,
            evidence_observation_ids=[],
            baseline_state_date=datetime(2027, 8, 3, tzinfo=UTC),
            horizon_months=6,
            random_seed=445567,
        )).output
        assert sequential.posterior.prior_posterior_id == first.posterior.posterior_id
        assert sequential.diagnostics.prior_posterior_id == first.posterior.posterior_id
        linked = production_repository.get_forecast(forecast.production_forecast_id, database_path=database)
        assert linked and linked["posterior_status"] == "available"
        assert linked["posterior"]["median"] == sequential.posterior.production_distribution.median

        counts = repository.summary(database_path=database)
        assert counts["bayesian_evidence_observations"] == 2
        assert counts["bayesian_posteriors"] == 3
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

        # Validate destructive rollback only on this disposable populated database.
        assert manager.downgrade_one(allow_destructive=True) == 5
        with closing(sqlite3.connect(database)) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "bayesian_posteriors" not in tables
            forecast_row = conn.execute(
                "SELECT posterior_status, posterior_json, probability_of_decline FROM production_forecasts_v3 WHERE id = ?",
                (str(forecast.production_forecast_id),),
            ).fetchone()
            assert forecast_row == ("not_run", None, None)
        assert manager.upgrade(target_version=5) == [5]

    result = (ROOT / "baseline_snapshots" / "phase5_test_results.txt").read_text(encoding="utf-8")
    assert "197 tests" in result
    assert "warning" not in result.lower()
    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": [1, 2, 3, 4, 5],
        "bayesian_engine": bayesian_engine.descriptor.engine_id,
        "bayesian_engine_version": bayesian_engine.descriptor.version,
        "parameter_version": BAYESIAN_PARAMETER_VERSION,
        "particle_range": [100, 5000],
        "evidence_requested": 2,
        "evidence_assimilated": 1,
    }, indent=2))
    print("PHASE 5 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
