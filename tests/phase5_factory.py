from __future__ import annotations

from datetime import UTC, datetime

from app.domain.bayesian import BayesianSimulationRequest, PalmStateVector
from app.engines.production import ProductionEngine
from tests.phase4_factory import prepare_phase4_foundation, prepare_phase4_weather, production_request


def prepare_phase5_production(*, farm_id=None, database_path=None):
    prepare_phase4_foundation(database_path=database_path)
    _, feature_set_id = prepare_phase4_weather(database_path=database_path)
    updates = {"farm_id": farm_id} if farm_id is not None else {}
    output = ProductionEngine(database_path=database_path).execute(
        production_request(feature_set_id, **updates)
    ).output
    return output


def initial_state() -> PalmStateVector:
    return PalmStateVector(
        young=25,
        healthy_bearing=320,
        aging=40,
        stressed=20,
        infested_or_diseased=5,
        rehabilitating=10,
        dead=5,
        soil_fertility_index=0.65,
        soil_water_index=0.60,
    )


def bayesian_request(forecast_id, **updates) -> BayesianSimulationRequest:
    payload = {
        "production_forecast_id": forecast_id,
        "initial_state": initial_state(),
        "baseline_state_date": datetime(2026, 8, 3, tzinfo=UTC),
        "horizon_months": 12,
        "particle_count": 300,
        "random_seed": 20260803,
        "intervention": "none",
        "farm_data_version": "phase5-test-farm-1",
    }
    payload.update(updates)
    return BayesianSimulationRequest.model_validate(payload)
