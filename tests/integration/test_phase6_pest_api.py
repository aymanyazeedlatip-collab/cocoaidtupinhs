from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from tests.phase6_factory import prepare_phase6_production

client = TestClient(app)


def test_phase6_status_profiles_observation_assessment_and_record_flow():
    production = prepare_phase6_production()
    status = client.get("/api/v2/pests/status")
    assert status.status_code == 200
    assert status.json()["engine"]["availability"] == "available"
    assert "asiatic-palm-weevil" in status.json()["supported_pest_profile_ids"]
    assert "red_palm_weevil" not in status.json()["supported_pest_profile_ids"]

    profiles = client.get("/api/v2/pests/profiles")
    assert profiles.status_code == 200
    assert len(profiles.json()["profiles"]) == 5

    observation_payload = {
        "farm_id": str(production.forecast.farm_id),
        "production_forecast_id": str(production.forecast.production_forecast_id),
        "pest_profile_id": "coconut-scale-insect",
        "factor_code": "scale_colonies",
        "evidence_status": "field_confirmed",
        "observed_at": datetime(2026, 8, 3, tzinfo=UTC).isoformat(),
        "value": True,
        "source_label": "manual field inspection"
    }
    observation = client.post("/api/v2/pests/observations", json=observation_payload)
    assert observation.status_code == 200
    observation_id = observation.json()["observation_id"]
    assert observation.json()["bayesian_link_created"] is False

    request = {
        "farm_id": str(production.forecast.farm_id),
        "production_forecast_id": str(production.forecast.production_forecast_id),
        "pest_profile_ids": ["coconut-scale-insect"],
        "assessed_at": datetime(2026, 8, 3, 8, tzinfo=UTC).isoformat(),
        "context": {
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
            "symptom_codes": ["scale_colonies_on_leaflets"]
        },
        "observation_ids": [observation_id],
        "nearby_confirmed_cases": [],
        "farm_data_version": "phase6-api-test"
    }
    response = client.post("/api/v2/pests/assess", json=request)
    assert response.status_code == 200, response.text
    result = response.json()["output"]
    assert result["assessments"][0]["expected_loss"] <= result["assessments"][0]["conditional_loss"]
    assessment_id = result["assessments"][0]["assessment_id"]

    record = client.get(f"/api/v2/pests/assessments/{assessment_id}")
    assert record.status_code == 200
    assert record.json()["pest_profile_id"] == "coconut-scale-insect"
    assert record.json()["evidence_contributions"]


def test_phase6_health_contract_and_migration():
    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["contract_api_version"] == "3.0.0-draft.10"
    migrations = health.json()["database_migrations"]
    assert migrations[5]["name"] == "phase6_pest_risk_inference"
    assert migrations[5]["state"] == "applied"
