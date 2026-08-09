from __future__ import annotations

from datetime import UTC, datetime

from app.domain.pest import PestAssessmentRequest, PestFarmContext
from tests.phase5_factory import prepare_phase5_production


def prepare_phase6_production(*, farm_id=None, database_path=None):
    return prepare_phase5_production(farm_id=farm_id, database_path=database_path)


def pest_context(**updates) -> PestFarmContext:
    payload = {
        "total_palms": 425,
        "young_palms": 25,
        "healthy_bearing_palms": 320,
        "aging_palms": 40,
        "stressed_palms": 20,
        "infested_or_diseased_palms": 5,
        "rehabilitating_palms": 10,
        "dead_palms": 5,
        "mean_palm_age_years": 18,
        "maintenance_quality": 0.55,
        "sanitation_quality": 0.55,
        "drainage_quality": 0.60,
        "waterlogging": False,
        "natural_enemies_present": False,
        "decaying_organic_breeding_material": False,
        "fresh_palm_wounds": False,
        "storm_damage": False,
        "symptom_codes": [],
    }
    payload.update(updates)
    return PestFarmContext.model_validate(payload)


def pest_request(production, **updates) -> PestAssessmentRequest:
    payload = {
        "farm_id": production.forecast.farm_id,
        "production_forecast_id": production.forecast.production_forecast_id,
        "pest_profile_ids": [
            "bud-nut-rot",
            "coconut-leaf-beetle",
            "rhinoceros-beetle",
            "asiatic-palm-weevil",
            "coconut-scale-insect",
        ],
        "assessed_at": datetime(2026, 8, 3, 8, tzinfo=UTC),
        "context": pest_context(),
        "observation_ids": [],
        "nearby_confirmed_cases": [],
        "farm_data_version": "phase6-test-farm-1",
    }
    payload.update(updates)
    return PestAssessmentRequest.model_validate(payload)
