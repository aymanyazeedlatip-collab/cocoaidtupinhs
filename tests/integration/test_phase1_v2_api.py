from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_legacy_and_contract_apis_coexist():
    legacy = client.get("/api/health")
    contract = client.get("/api/v2/health")
    assert legacy.status_code == 200
    assert legacy.json()["api_version"] == "2.11.0"
    assert contract.status_code == 200
    assert contract.json()["product"] == "COCOAID"
    assert contract.json()["contract_api_version"] == "3.0.0-draft.10"


def test_request_context_headers_are_attached_without_client_changes():
    response = client.get("/api/v2/configuration", headers={"X-Request-ID": "phase1-test"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "phase1-test"
    assert float(response.headers["X-Process-Time-Ms"]) >= 0


def test_contract_catalog_schema_and_validation_endpoint():
    catalog = client.get("/api/v2/contracts")
    assert catalog.status_code == 200
    names = {item["name"] for item in catalog.json()["contracts"]}
    assert "WeatherModelRun" in names
    schema = client.get("/api/v2/contracts/WeatherModelRun")
    assert schema.status_code == 200
    assert schema.json()["json_schema"]["title"] == "WeatherModelRun"

    now = datetime.now(UTC)
    payload = {
        "provider": "Open-Meteo",
        "provider_model": "auto",
        "data_kind": "forecast",
        "model_run_at": now.isoformat(),
        "retrieved_at": now.isoformat(),
        "valid_from": now.isoformat(),
        "valid_to": (now + timedelta(days=16)).isoformat(),
        "latitude": 6.334,
        "longitude": 124.952,
        "variables": ["precipitation"],
        "units": {"precipitation": "mm"},
        "source": {
            "source_id": "open-meteo",
            "title": "Open-Meteo forecast",
            "source_type": "weather_provider"
        }
    }
    valid = client.post("/api/v2/contracts/WeatherModelRun/validate", json=payload)
    assert valid.status_code == 200
    assert valid.json()["valid"] is True

    payload["valid_to"] = (now + timedelta(days=17)).isoformat()
    invalid = client.post("/api/v2/contracts/WeatherModelRun/validate", json=payload)
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"
    assert "16 days" in invalid.json()["detail"]


def test_unknown_contract_and_engine_use_structured_errors():
    contract = client.get("/api/v2/contracts/DoesNotExist")
    assert contract.status_code == 404
    assert contract.json()["code"] == "contract_not_found"
    assert contract.json()["request_id"]

    engine = client.get("/api/v2/engines/does.not.exist")
    assert engine.status_code == 404
    assert engine.json()["code"] == "engine_not_found"


def test_registries_and_migration_status_are_exposed_read_only():
    engines = client.get("/api/v2/engines").json()["engines"]
    assert any(item["engine_id"] == "v3.bayesian" and item["availability"] == "available" for item in engines)
    assert client.get("/api/v2/parameters").status_code == 200
    assert client.get("/api/v2/units").status_code == 200
    models = client.get("/api/v2/models").json()
    assert models["models"]["production"]["artifact"]["sha256"]
    migrations = client.get("/api/v2/database/migrations").json()["migrations"]
    assert migrations[0]["state"] == "applied"


def test_openapi_includes_v2_contract_endpoints_and_legacy_endpoints():
    schema = client.get("/openapi.json").json()
    assert "/api/health" in schema["paths"]
    assert "/api/v2/contracts" in schema["paths"]
    assert "/api/v2/contracts/{contract_name}/validate" in schema["paths"]
