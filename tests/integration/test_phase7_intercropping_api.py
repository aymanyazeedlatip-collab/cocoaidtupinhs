from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from tests.phase7_factory import prepare_phase7_production

client = TestClient(app)


def test_phase7_status_candidates_assessment_and_record_flow():
    production = prepare_phase7_production()
    status = client.get("/api/v2/intercropping/status")
    assert status.status_code == 200
    assert status.json()["engine"]["availability"] == "available"
    assert status.json()["model_type"] == "evidence_scoring"

    candidates = client.get("/api/v2/intercropping/candidates?candidate_id=cacao")
    assert candidates.status_code == 200
    assert candidates.json()["count"] == 1
    assert candidates.json()["candidates"][0]["profile_version"] == "intercrop-requirements-1.0.0"

    cell_id = uuid4()
    payload = {
        "farm_id": str(production.forecast.farm_id),
        "production_forecast_id": str(production.forecast.production_forecast_id),
        "posterior_id": None,
        "pest_assessment_run_id": None,
        "assessed_at": datetime(2026, 8, 3, 8, tzinfo=UTC).isoformat(),
        "candidate_ids": ["cacao", "coffee", "sugarcane"],
        "cells": [{
            "cell_id": str(cell_id), "label": "API Cell A", "area_hectares": 1.0,
            "palm_age_years": 40, "spacing_x_m": 8, "spacing_y_m": 8,
            "canopy_design": "square", "canopy_density_index": 0.65,
            "row_orientation_degrees": None, "slope_degrees": 4,
            "drainage_index": 0.65, "soil_ph": 6.1, "soil_moisture_index": 0.58,
            "nitrogen_index": 0.65, "available_space_fraction": 0.70,
            "management_feasibility": 0.72, "market_access_index": 0.60
        }],
        "farm_data_version": "phase7-api-test",
        "include_economic_potential": True
    }
    response = client.post("/api/v2/intercropping/assess", json=payload)
    assert response.status_code == 200, response.text
    output = response.json()["output"]
    assert output["summary"]["total_assessment_count"] == 3
    assert output["weather_feature_set_id"]
    assessment_id = output["assessments"][0]["assessment_id"]

    record = client.get(f"/api/v2/intercropping/assessments/{assessment_id}")
    assert record.status_code == 200
    assert record.json()["components"]

    listing = client.get(f"/api/v2/intercropping/assessments?cell_id={cell_id}")
    assert listing.status_code == 200
    assert listing.json()["count"] == 3


def test_phase7_health_contract_and_migration():
    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["contract_api_version"] == "3.0.0-draft.10"
    migrations = health.json()["database_migrations"]
    assert migrations[6]["name"] == "phase7_intercropping_potential"
    assert migrations[6]["state"] == "applied"
