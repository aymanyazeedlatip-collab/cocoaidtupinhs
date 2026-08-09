from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import FarmSiteForecastRequest
from app.schemas.weather import WeatherGridRequest
from app.services.cache import cache
from app.services.persistent_cache import persistent_cache
from app.weather import providers

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_farm_site_schema_accepts_legacy_5000_run_setting():
    request = FarmSiteForecastRequest(runs=5000)
    assert request.runs == 5000


def test_422_response_is_human_readable_instead_of_object_object():
    response = client.post(
        "/api/farm-site/forecast",
        json={"runs": 0, "start_year": 2026, "end_year": 2050},
    )
    assert response.status_code == 422
    payload = response.json()
    assert isinstance(payload["detail"], str)
    assert "runs" in payload["detail"]
    assert "[object Object]" not in payload["detail"]
    assert payload["errors"][0]["field"]


def test_frontend_normalizes_stale_settings_and_blocks_duplicate_forecast_requests():
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function normalizeRunCount(value)" in js
    assert "ALLOWED_SIMULATION_RUNS" in js
    assert "forecastRequestInFlight" in js
    assert "A forecast is already running" in js
    assert "formatApiErrorDetail" in js
    assert 'button.disabled = true' in js


def test_productivity_wind_reuses_weather_gis_style_without_changing_climate_model_contract():
    main_js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    main_html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    viewer_js = (ROOT / "app" / "static" / "weather-viewer" / "app.js").read_text(encoding="utf-8")
    assert "function drawForecastWindArrow" in main_js
    assert 'id="forecastWindCanvas"' in main_html
    assert "forecastApplyTerrainDeflection" in main_js
    assert "function drawWindArrow" in viewer_js
    assert "function applyTerrainDeflection" in viewer_js
    assert "function terrainAt" in viewer_js
    assert "elevation_m: cube.elevation_m || null" in viewer_js


def test_weather_grid_preserves_provider_elevation_for_terrain_flow(monkeypatch, tmp_path):
    async def fake_get_json(_url, _params):
        points = []
        for index in range(9):
            points.append(
                {
                    "elevation": 100 + index * 50,
                    "hourly": {
                        "time": ["2026-07-20T00:00", "2026-07-20T01:00"],
                        "wind_speed_10m": [12.0, 13.0],
                        "wind_direction_10m": [90.0, 95.0],
                    },
                }
            )
        return points

    monkeypatch.setattr(providers, "get_json", fake_get_json)
    monkeypatch.setattr(providers.settings, "offline_mode", False)
    monkeypatch.setattr(providers.settings, "cache_dir", tmp_path)
    monkeypatch.setattr(persistent_cache, "directory", tmp_path)
    cache._items.clear()
    # Use a unique bounding box so no packaged persistent-cache value can match.
    request = WeatherGridRequest(
        west=130.11,
        south=10.11,
        east=130.61,
        north=10.61,
        rows=3,
        cols=3,
        variables=["wind_speed_10m", "wind_direction_10m"],
        forecast_hours=12,
    )
    result = asyncio.run(providers.weather_grid(request))
    assert result["elevation_m"] == [
        [100.0, 150.0, 200.0],
        [250.0, 300.0, 350.0],
        [400.0, 450.0, 500.0],
    ]
    assert "terrain_note" in result["metadata"]
