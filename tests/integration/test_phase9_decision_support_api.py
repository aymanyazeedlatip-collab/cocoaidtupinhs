from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.phase9_factory import decision_request, prepare_phase9_records

client = TestClient(app)


def test_phase9_status_compose_list_and_retrieve():
    production, posterior, pest, intercrop, rehabilitation = prepare_phase9_records()
    status = client.get("/api/v2/decision-support/status")
    assert status.status_code == 200
    assert status.json()["engine"]["availability"] == "available"
    assert status.json()["safety_policy"]["overwrites_source_engines"] is False

    request = decision_request(production, posterior, pest, intercrop, rehabilitation)
    response = client.post("/api/v2/decision-support/compose", json=request.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    output = response.json()["output"]
    assert output["record"]["status"] == "completed"
    run_id = output["record"]["analysis_run_id"]

    record = client.get(f"/api/v2/decision-support/runs/{run_id}")
    assert record.status_code == 200
    assert len(record.json()["component_results"]) == 5
    listing = client.get(f"/api/v2/decision-support/runs?farm_id={production.forecast.farm_id}")
    assert listing.status_code == 200
    assert listing.json()["count"] >= 1


def test_phase9_health_contract_and_migration():
    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["contract_api_version"] == "3.0.0-draft.10"
    migrations = health.json()["database_migrations"]
    assert migrations[8]["name"] == "phase9_integrated_decision_support"
    assert migrations[8]["state"] == "applied"
