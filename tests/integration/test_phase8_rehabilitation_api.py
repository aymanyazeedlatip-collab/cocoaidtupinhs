from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.phase8_factory import prepare_phase8_dependencies, rehabilitation_request

client = TestClient(app)


def test_phase8_status_plan_listing_and_record_flow():
    production, pest, intercrop, cell_id = prepare_phase8_dependencies()
    status = client.get("/api/v2/rehabilitation/status")
    assert status.status_code == 200
    assert status.json()["engine"]["availability"] == "available"
    assert status.json()["safety_policy"]["predicted_hazards_are_confirmed_damage"] is False
    request = rehabilitation_request(production, pest, intercrop, cell_id)
    response = client.post("/api/v2/rehabilitation/plan", json=request.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    output = response.json()["output"]
    assert len(output["plan"]["scenarios"]) == 6
    assert output["summary"]["assessed_cell_count"] == 1
    plan_id = output["plan"]["rehabilitation_plan_id"]
    record = client.get(f"/api/v2/rehabilitation/plans/{plan_id}")
    assert record.status_code == 200
    assert len(record.json()["scenarios"]) == 6
    listing = client.get(f"/api/v2/rehabilitation/plans?farm_id={production.forecast.farm_id}")
    assert listing.status_code == 200
    assert listing.json()["count"] >= 1


def test_phase8_health_contract_and_migration():
    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["contract_api_version"] == "3.0.0-draft.10"
    migrations = health.json()["database_migrations"]
    assert migrations[7]["name"] == "phase8_rehabilitation_scenario_optimization"
    assert migrations[7]["state"] == "applied"
