from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.data_foundation.seeding import seed_reference_data
from app.main import app
from tests.phase4_factory import prepare_phase4_weather

client = TestClient(app)


def _request(feature_set_id: str, farm_id: str) -> dict:
    return {
        "farm_id": farm_id,
        "weather_feature_set_id": feature_set_id,
        "farm_area_hectares": 5,
        "productive_trees": 320,
        "aging_trees": 40,
        "stressed_trees": 20,
        "infested_trees": 5,
        "recovering_trees": 10,
        "soil_ph": 6.1,
        "nitrogen_index": 0.65,
        "phosphorus_index": 0.60,
        "potassium_index": 0.70,
        "suitability_score": 0.78,
        "pest_probability": 0.12,
        "variety_id": "agdt",
        "variety_class": "Unknown",
        "intervention": "none",
        "baseline_annual_production_tons": 25,
        "young_nut_share": 0.03,
    }


def test_phase4_production_api_full_persistence_and_performance_flow():
    seed_reference_data()
    _, feature_set_id = prepare_phase4_weather()
    farm_id = str(uuid4())
    response = client.post("/api/v2/production/forecast", json=_request(feature_set_id, farm_id))
    assert response.status_code == 200, response.text
    body = response.json()
    forecast = body["output"]["forecast"]
    forecast_id = forecast["production_forecast_id"]
    assert forecast["posterior_status"] == "not_run"
    assert forecast["posterior_prediction"] is None
    assert forecast["variety_id"] == "agdt"

    status = client.get("/api/v2/production/status")
    assert status.status_code == 200
    assert status.json()["engine"]["availability"] == "available"
    assert len(status.json()["frozen_feature_order"]) == 19

    listing = client.get("/api/v2/production/forecasts", params={"farm_id": farm_id})
    assert listing.status_code == 200 and listing.json()["count"] == 1
    stored = client.get(f"/api/v2/production/forecasts/{forecast_id}")
    assert stored.status_code == 200
    assert stored.json()["feature_adapter_version"] == "production-feature-adapter-1.0.0"

    actual = client.post("/api/v2/production/actuals", json={
        "farm_id": farm_id,
        "forecast_id": forecast_id,
        "product": "whole_nut_with_husk",
        "period_start": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "period_end": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
        "quantity": forecast["variety_adjusted_prediction"],
        "unit": "t",
        "source_type": "measured",
    })
    assert actual.status_code == 200
    performance = client.get(f"/api/v2/production/forecasts/{forecast_id}/performance")
    assert performance.status_code == 200
    assert performance.json()["compatible_actual_count"] == 1


def test_phase4_intercrop_assessment_and_openapi_are_sanitized():
    seed_reference_data()
    response = client.get("/api/v2/data-foundation/intercrop-income-assessment")
    assert response.status_code == 200
    body = response.json()
    assert body["intercrop_record_count"] == 127
    assert body["privacy"]["farmer_names_exposed"] is False
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/api/v2/production/status", "/api/v2/production/forecast",
        "/api/v2/production/forecasts", "/api/v2/production/forecasts/{forecast_id}",
        "/api/v2/production/actuals", "/api/v2/production/forecasts/{forecast_id}/performance",
        "/api/v2/data-foundation/intercrop-income-assessment",
    ):
        assert path in paths


def test_phase4_health_exposes_current_contract_and_migration():
    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["contract_api_version"] == "3.0.0-draft.10"
    migrations = health.json()["database_migrations"]
    assert migrations[3]["name"] == "phase4_production_engine"
    assert migrations[3]["state"] == "applied"
