from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.weather import providers
from tests.weather_factory import make_open_meteo_payload

client = TestClient(app)


def test_phase3_weather_assimilation_api_persists_versions_and_hides_history(monkeypatch):
    reference_at = datetime.now(UTC)
    payloads = [
        make_open_meteo_payload(reference_at=reference_at),
        make_open_meteo_payload(forecast_rain_adjustment=1.0, reference_at=reference_at),
    ]

    async def fake_fetch(request, force_refresh=False):
        return payloads.pop(0)

    monkeypatch.setattr(providers, "fetch_point_forecast", fake_fetch)
    request = {
        "latitude": 6.334,
        "longitude": 124.952,
        "forecast_days": 16,
        "history_days": 90,
        "force_refresh": True,
    }
    first = client.post("/api/v2/weather/assimilate", json=request)
    assert first.status_code == 200, first.text
    first_body = first.json()
    first_id = first_body["weather_run"]["id"]
    assert first_body["weather_run"]["requested_forecast_days"] == 16
    assert first_body["feature_set"]["features"]
    assert first_body["live_forecast"]["historical_values_included"] is False
    assert len(first_body["live_forecast"]["daily"]["time"]) == 16
    assert all(day >= reference_at.astimezone().date().isoformat() for day in first_body["live_forecast"]["daily"]["time"])

    second = client.post("/api/v2/weather/assimilate", json=request)
    assert second.status_code == 200, second.text
    second_id = second.json()["weather_run"]["id"]
    assert second_id != first_id

    status = client.get("/api/v2/weather/status")
    assert status.status_code == 200
    assert status.json()["live_forecast_limit_days"] == 16
    assert status.json()["storage"]["counts"]["weather_model_runs"] == 2

    runs = client.get("/api/v2/weather/runs")
    assert runs.status_code == 200
    assert runs.json()["count"] == 2

    stored = client.get(f"/api/v2/weather/runs/{first_id}", params={"include_values": True})
    assert stored.status_code == 200
    assert {value["period_kind"] for value in stored.json()["values"]} == {"historical", "current", "forecast"}

    features = client.get(f"/api/v2/weather/runs/{first_id}/features")
    assert features.status_code == 200
    assert len(features.json()["features"]) == 14

    comparison = client.get(
        "/api/v2/weather/compare",
        params={"base_run_id": first_id, "comparison_run_id": second_id},
    )
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()["metrics"]["precipitation_sum"]["mean_change"] == 1.0


def test_phase3_weather_api_enforces_sixteen_day_limit():
    response = client.post("/api/v2/weather/assimilate", json={
        "latitude": 6.334, "longitude": 124.952, "forecast_days": 17, "history_days": 90,
    })
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_phase3_openapi_and_health_expose_weather_contracts_and_migration():
    health = client.get("/api/v2/health")
    assert health.status_code == 200
    assert health.json()["contract_api_version"] == "3.0.0-draft.10"
    migrations = client.get("/api/v2/database/migrations").json()["migrations"]
    assert migrations[2]["state"] == "applied"
    assert migrations[2]["name"] == "phase3_weather_assimilation"

    schema = client.get("/openapi.json").json()
    for path in (
        "/api/v2/weather/status",
        "/api/v2/weather/assimilate",
        "/api/v2/weather/runs",
        "/api/v2/weather/runs/{run_id}",
        "/api/v2/weather/runs/{run_id}/features",
        "/api/v2/weather/compare",
    ):
        assert path in schema["paths"]


def test_weather_provider_failure_returns_actionable_nonblank_details(monkeypatch):
    from app.api.v2 import routes as v2_routes
    from app.core.errors import ProviderUnavailableError

    async def fail_assimilation(request):
        raise ProviderUnavailableError(
            "Weather provider connection failed after 2 attempt(s): ConnectError: certificate verify failed",
            details={
                "provider_host": "api.open-meteo.com",
                "attempts": [
                    {"mode": "environment", "attempt": 1, "exception_type": "ConnectError", "message": "certificate verify failed"},
                    {"mode": "direct", "attempt": 1, "exception_type": "ConnectError", "message": "certificate verify failed"},
                ],
                "troubleshooting": ["Run check_weather_provider.bat"],
            },
        )

    monkeypatch.setattr(v2_routes, "assimilate_weather", fail_assimilation)
    response = client.post("/api/v2/weather/assimilate", json={
        "latitude": 6.334,
        "longitude": 124.952,
        "forecast_days": 16,
        "history_days": 90,
        "force_refresh": True,
    })

    assert response.status_code == 503
    body = response.json()
    assert body["detail"].strip()
    assert "ConnectError" in body["detail"]
    assert body["details"]["provider_host"] == "api.open-meteo.com"
    assert {item["mode"] for item in body["details"]["attempts"]} == {"environment", "direct"}
    assert body["provider_error"] is True
