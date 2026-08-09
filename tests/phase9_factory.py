from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.bayesian import BayesianSimulationRequest
from app.domain.decision_support import DecisionSupportRequest
from app.domain.enums import EvidenceStatus
from app.domain.intercropping import IntercropAssessmentRequest
from app.domain.pest import PestObservation
from app.engines.bayesian import BayesianEngine
from app.engines.intercropping import IntercroppingEngine
from app.engines.pest_inference import PestInferenceEngine
from app.engines.rehabilitation import RehabilitationEngine
from app.pest import repository as pest_repository
from tests.phase5_factory import bayesian_request
from tests.phase6_factory import pest_context, pest_request
from tests.phase7_factory import cell_context, prepare_phase7_production
from tests.phase8_factory import rehabilitation_cell, rehabilitation_request


def prepare_phase9_records(*, database_path=None):
    production = prepare_phase7_production(database_path=database_path)
    posterior = BayesianEngine(database_path=database_path).execute(
        bayesian_request(production.forecast.production_forecast_id)
    ).output
    cell_id = uuid4()
    observation = PestObservation(
        farm_id=production.forecast.farm_id,
        cell_id=cell_id,
        production_forecast_id=production.forecast.production_forecast_id,
        pest_profile_id="coconut-scale-insect",
        factor_code="scale_colonies",
        evidence_status=EvidenceStatus.FIELD_CONFIRMED,
        observed_at=datetime(2026, 8, 4, 1, tzinfo=UTC),
        value=True,
        unit="fraction",
        prevalence_fraction=0.15,
        source_label="Phase 9 integration test",
    )
    observation_id, _ = pest_repository.save_observation(observation, database_path=database_path)
    pest = PestInferenceEngine(database_path=database_path).execute(pest_request(
        production,
        cell_id=cell_id,
        posterior_id=posterior.posterior.posterior_id,
        observation_ids=[observation_id],
        context=pest_context(
            total_palms=425, young_palms=25, healthy_bearing_palms=270,
            aging_palms=60, stressed_palms=25, infested_or_diseased_palms=25,
            rehabilitating_palms=10, dead_palms=10,
            maintenance_quality=0.45, sanitation_quality=0.45, drainage_quality=0.35,
            symptom_codes=["scale_colonies_on_leaflets"],
        ),
    )).output
    intercrop = IntercroppingEngine(database_path=database_path).execute(
        IntercropAssessmentRequest(
            farm_id=production.forecast.farm_id,
            production_forecast_id=production.forecast.production_forecast_id,
            posterior_id=posterior.posterior.posterior_id,
            pest_assessment_run_id=pest.run_id,
            assessed_at=datetime(2026, 8, 4, 2, tzinfo=UTC),
            candidate_ids=["cacao", "coffee", "banana", "sugarcane"],
            cells=[cell_context(cell_id=cell_id, label="Phase 9 Cell")],
            farm_data_version="phase9-test-farm-1",
            include_economic_potential=True,
        )
    ).output
    rehab_request = rehabilitation_request(
        production, pest, intercrop, cell_id,
        posterior_id=posterior.posterior.posterior_id,
        planned_at=datetime(2026, 8, 4, 3, tzinfo=UTC),
        cells=[rehabilitation_cell(cell_id, label="Phase 9 Cell")],
        farm_data_version="phase9-test-farm-1",
    )
    rehabilitation = RehabilitationEngine(database_path=database_path).execute(rehab_request).output
    return production, posterior, pest, intercrop, rehabilitation


def decision_request(production, posterior, pest, intercrop, rehabilitation, **updates):
    payload = {
        "farm_id": production.forecast.farm_id,
        "production_forecast_id": production.forecast.production_forecast_id,
        "posterior_id": posterior.posterior.posterior_id,
        "pest_assessment_run_id": pest.run_id,
        "intercropping_run_id": intercrop.run_id,
        "rehabilitation_plan_id": rehabilitation.plan.rehabilitation_plan_id,
        "generated_at": datetime(2026, 8, 4, 4, tzinfo=UTC),
        "requested_components": ["production", "bayesian", "pest", "intercropping", "rehabilitation"],
        "failure_policy": "continue_optional",
        "farm_data_version": "phase9-test-farm-1",
    }
    payload.update(updates)
    return DecisionSupportRequest.model_validate(payload)
