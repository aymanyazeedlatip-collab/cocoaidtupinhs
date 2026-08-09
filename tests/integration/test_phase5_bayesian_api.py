from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from tests.phase5_factory import prepare_phase5_production, initial_state

client = TestClient(app)


def test_phase5_bayesian_api_observation_simulation_and_persistence_flow():
    farm_id = uuid4()
    production = prepare_phase5_production(farm_id=farm_id)
    forecast_id = str(production.forecast.production_forecast_id)
    observation = client.post("/api/v2/bayesian/observations", json={
        "farm_id": str(farm_id),
        "production_forecast_id": forecast_id,
        "evidence_type": "actual_rainfall",
        "evidence_status": "field_confirmed",
        "observed_at": datetime(2026, 8, 5, tzinfo=UTC).isoformat(),
        "value": 48,
        "unit": "mm",
        "source_label": "manual rain gauge",
    })
    assert observation.status_code == 200, observation.text
    observation_id = observation.json()["observation_id"]
    assert observation.json()["will_update_posterior"] is True

    response = client.post("/api/v2/bayesian/simulate", json={
        "production_forecast_id": forecast_id,
        "initial_state": initial_state().model_dump(mode="json"),
        "baseline_state_date": datetime(2026, 8, 3, tzinfo=UTC).isoformat(),
        "horizon_months": 12,
        "particle_count": 300,
        "random_seed": 12345,
        "intervention": "none",
        "evidence_observation_ids": [observation_id],
        "farm_data_version": "api-test-farm-1",
    })
    assert response.status_code == 200, response.text
    body = response.json()["output"]
    posterior_id = body["posterior"]["posterior_id"]
    assert body["posterior"]["production_distribution"]["lower"] >= 0
    assert body["diagnostics"]["palm_count_conserved"] is True
    assert body["diagnostics"]["evidence_count_used"] == 1

    status = client.get("/api/v2/bayesian/status")
    assert status.status_code == 200
    assert status.json()["engine"]["availability"] == "available"
    assert status.json()["parameter_version"] == "bayesian-farm-state-parameters-1.0.0"

    listing = client.get("/api/v2/bayesian/posteriors", params={"farm_id": str(farm_id)})
    assert listing.status_code == 200 and listing.json()["count"] == 1
    stored = client.get(f"/api/v2/bayesian/posteriors/{posterior_id}")
    assert stored.status_code == 200
    assert stored.json()["diagnostics"]["random_seed"] == 12345

    forecast = client.get(f"/api/v2/production/forecasts/{forecast_id}")
    assert forecast.status_code == 200
    assert forecast.json()["posterior_status"] == "available"


def test_phase5_health_contract_openapi_and_migration():
    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["contract_api_version"] == "3.0.0-draft.10"
    migrations = health.json()["database_migrations"]
    assert migrations[4]["name"] == "phase5_bayesian_farm_state"
    assert migrations[4]["state"] == "applied"
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/api/v2/bayesian/status", "/api/v2/bayesian/observations",
        "/api/v2/bayesian/simulate", "/api/v2/bayesian/posteriors",
        "/api/v2/bayesian/posteriors/{posterior_id}",
    ):
        assert path in paths
