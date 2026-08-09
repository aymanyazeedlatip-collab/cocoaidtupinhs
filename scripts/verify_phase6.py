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
from app.domain.enums import EngineAvailability, EvidenceStatus
from app.domain.pest import NearbyConfirmedPestCase, PestObservation
from app.engines.pest_inference import PEST_ENGINE_VERSION, PestInferenceEngine, pest_inference_engine
from app.parameters.registry import parameter_registry
from app.pest import repository
from app.pest.parameters import (
    PARAMETERS,
    PEST_PARAMETER_SET_ID,
    PEST_PARAMETER_VERSION,
    SUPPORTED_PEST_IDS,
)
from app.storage.migrations import MigrationManager
from tests.phase6_factory import pest_request, prepare_phase6_production

REQUIRED_ARTIFACTS = [
    "docs/phase_6/ARCHITECTURE.md",
    "docs/phase_6/DATA_CONTRACTS.md",
    "docs/phase_6/INFERENCE_MODEL.md",
    "docs/phase_6/DATABASE_SCHEMA.md",
    "docs/phase_6/API.md",
    "docs/phase_6/LIMITATIONS.md",
    "docs/phase_6/TEST_REPORT.md",
    "docs/phase_6/USER_ACTIONS.md",
    "docs/phase_6/PHASE_6_STATUS.md",
    "docs/phase_6/RELEASE_NOTES.md",
    "manifests/phase6_contract_hashes.json",
    "manifests/phase6_engine_catalog.json",
    "manifests/phase6_endpoint_catalog.json",
    "manifests/phase6_migration_catalog.json",
    "manifests/phase6_parameter_catalog.json",
    "manifests/phase6_pest_profile_catalog.json",
    "baseline_snapshots/phase6_test_results.txt",
]


def _assessment(output, pest_id: str):
    return next(item for item in output.assessments if item.profile.pest_profile_id == pest_id)


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 6 artifact: {relative}"

    assert settings.contract_api_version == "3.0.0-draft.10"
    assert pest_inference_engine.descriptor.availability == EngineAvailability.AVAILABLE
    assert pest_inference_engine.descriptor.version == PEST_ENGINE_VERSION == "1.0.0"
    assert tuple(SUPPORTED_PEST_IDS) == (
        "bud-nut-rot",
        "coconut-leaf-beetle",
        "rhinoceros-beetle",
        "asiatic-palm-weevil",
        "coconut-scale-insect",
    )
    assert "red_palm_weevil" not in SUPPORTED_PEST_IDS

    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == PEST_PARAMETER_SET_ID
    )
    assert descriptor.version == PEST_PARAMETER_VERSION
    values = parameter_registry.values(PEST_PARAMETER_SET_ID, PEST_PARAMETER_VERSION)
    assert values == PARAMETERS
    assert values["evidence_reliability"]["predicted"] == 0.0
    assert values["evidence_reliability"]["suspected"] == 0.0
    assert values["evidence_reliability"]["expert_confirmed"] == 1.0

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase6-") as temp:
        database = Path(temp) / "phase6.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=6) == [1, 2, 3, 4, 5, 6]
        assert manager.upgrade(target_version=6) == []

        production = prepare_phase6_production(database_path=database)
        forecast = production.forecast
        engine = PestInferenceEngine(database_path=database)

        baseline = engine.execute(pest_request(
            production,
            pest_profile_ids=["coconut-scale-insect"],
        )).output
        baseline_probability = baseline.assessments[0].outbreak_probability

        predicted = PestObservation(
            farm_id=forecast.farm_id,
            production_forecast_id=forecast.production_forecast_id,
            pest_profile_id="coconut-scale-insect",
            factor_code="scale_colonies",
            evidence_status=EvidenceStatus.PREDICTED,
            observed_at=datetime(2026, 8, 3, tzinfo=UTC),
            value=True,
            source_label="forecast-only verification evidence",
        )
        predicted_id, predicted_bayesian_id = repository.save_observation(
            predicted, database_path=database
        )
        assert predicted_bayesian_id is None
        predicted_output = engine.execute(pest_request(
            production,
            pest_profile_ids=["coconut-scale-insect"],
            observation_ids=[predicted_id],
        )).output
        assert predicted_output.assessments[0].outbreak_probability == baseline_probability
        assert predicted_output.evidence_audit[0]["used_for_probability"] is False

        confirmed = PestObservation(
            farm_id=forecast.farm_id,
            production_forecast_id=forecast.production_forecast_id,
            pest_profile_id="coconut-scale-insect",
            factor_code="confirmed_prevalence",
            evidence_status=EvidenceStatus.FIELD_CONFIRMED,
            observed_at=datetime(2026, 8, 4, tzinfo=UTC),
            value=0.30,
            unit="fraction",
            prevalence_fraction=0.30,
            source_label="field-count verification evidence",
        )
        confirmed_id, confirmed_bayesian_id = repository.save_observation(
            confirmed, database_path=database
        )
        assert confirmed_bayesian_id is not None
        confirmed_output = engine.execute(pest_request(
            production,
            pest_profile_ids=["coconut-scale-insect"],
            observation_ids=[confirmed_id],
        )).output
        confirmed_assessment = confirmed_output.assessments[0]
        assert confirmed_assessment.outbreak_probability > baseline_probability
        assert confirmed_output.evidence_audit[0]["used_for_probability"] is True
        assert confirmed_output.evidence_audit[0]["bayesian_observation_id"] == str(confirmed_bayesian_id)
        assert confirmed_assessment.expected_loss == (
            confirmed_assessment.outbreak_probability * confirmed_assessment.conditional_loss
        )
        assert confirmed_assessment.expected_loss <= confirmed_assessment.conditional_loss

        close_output = engine.execute(pest_request(
            production,
            pest_profile_ids=["coconut-scale-insect"],
            nearby_confirmed_cases=[NearbyConfirmedPestCase(
                pest_profile_id="coconut-scale-insect",
                distance_m=100,
                evidence_status=EvidenceStatus.FIELD_CONFIRMED,
            )],
        )).output
        far_output = engine.execute(pest_request(
            production,
            pest_profile_ids=["coconut-scale-insect"],
            nearby_confirmed_cases=[NearbyConfirmedPestCase(
                pest_profile_id="coconut-scale-insect",
                distance_m=10_000,
                evidence_status=EvidenceStatus.FIELD_CONFIRMED,
            )],
        )).output
        close_assessment = close_output.assessments[0]
        far_assessment = far_output.assessments[0]
        assert close_assessment.spatial_pressure > far_assessment.spatial_pressure
        assert close_assessment.outbreak_probability > far_assessment.outbreak_probability

        all_profiles = engine.execute(pest_request(production)).output
        assert len(all_profiles.assessments) == 5
        assert {item.profile.pest_profile_id for item in all_profiles.assessments} == set(SUPPORTED_PEST_IDS)
        assert "not merged" in all_profiles.taxonomy_notice.lower()
        for assessment in all_profiles.assessments:
            assert 0 <= assessment.outbreak_probability <= 1
            assert assessment.expected_loss <= assessment.conditional_loss
            assert assessment.expected_loss == assessment.outbreak_probability * assessment.conditional_loss
            assert assessment.evidence_contributions
            assert assessment.management_actions

        persisted = repository.get_assessment(
            confirmed_assessment.assessment_id, database_path=database
        )
        assert persisted is not None
        assert persisted["pest_profile_id"] == "coconut-scale-insect"
        assert persisted["evidence_contributions"]
        assert persisted["management_actions"]

        counts = repository.summary(database_path=database)
        assert counts["pest_observations_v3"] == 2
        assert counts["pest_assessment_runs"] == 6
        assert counts["pest_assessments_v3"] == 10
        assert counts["pest_assessment_contributions"] > 0
        assert counts["pest_assessment_actions"] > 0

        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            linked = conn.execute(
                "SELECT id FROM bayesian_evidence_observations WHERE id = ?",
                (str(confirmed_bayesian_id),),
            ).fetchone()
            assert linked is not None

        assert manager.downgrade_one(allow_destructive=True) == 6
        with closing(sqlite3.connect(database)) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            assert "pest_assessments_v3" not in tables
            assert "bayesian_posteriors" in tables
        assert manager.upgrade(target_version=6) == [6]

    result = (ROOT / "baseline_snapshots" / "phase6_test_results.txt").read_text(
        encoding="utf-8"
    )
    assert "210 tests" in result
    assert "62 fully isolated test-file processes" in result
    assert "warning" not in result.lower()

    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": [1, 2, 3, 4, 5, 6],
        "pest_engine": pest_inference_engine.descriptor.engine_id,
        "pest_engine_version": PEST_ENGINE_VERSION,
        "parameter_version": PEST_PARAMETER_VERSION,
        "supported_profiles": list(SUPPORTED_PEST_IDS),
        "predicted_evidence_changed_probability": False,
        "confirmed_prevalence_linked_to_bayesian": True,
        "conditional_expected_loss_separated": True,
        "spatial_decay_verified": True,
    }, indent=2))
    print("PHASE 6 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
