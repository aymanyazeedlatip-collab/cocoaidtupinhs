from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")


def test_version_and_extreme_weather_navigation_contract():
    client = TestClient(app)
    assert client.get("/api/health").json()["api_version"] == "2.11.0"
    assert 'id="hazardPrevEvent"' in HTML
    assert 'id="hazardNextEvent"' in HTML
    assert "function changeHazardEvent(delta)" in JS
    assert 'changeHazardEvent(-1)' in JS
    assert 'changeHazardEvent(1)' in JS
    assert ".hazard-event-navigator" in CSS


def test_loading_screen_is_minimal_and_accessible():
    loading = HTML.split('id="loadingOverlay"', 1)[1].split("</div>\n<script", 1)[0]
    assert "loading-logo-ring" in loading
    assert 'id="loadingTip"' in loading
    assert "loading-wordmark" not in loading
    assert "loading-progress" not in loading
    assert 'class="loading-status-text" id="loadingText"' in loading
    assert 'loading-mini-hologram' in loading


def test_priority_cells_and_formula_catalog_layout():
    assert 'id="healthPriorityCells"' in HTML
    assert "flex-direction: column" in CSS.split("/* Keep the priority value", 1)[1]
    assert 'id="formulaCatalogTitle"' in HTML
    assert "Bayesian evidence update" in HTML
    assert "Farm-state transition" in HTML
    assert "Expected utility" in HTML
    assert HTML.count("formula-catalog") >= 1


def test_climate_map_fits_farm_polygon_once():
    assert "function farmForecastBounds()" in JS
    assert "function fitForecastMapToFarm(force = false)" in JS
    assert "map.fitBounds(bounds, { padding: [92, 92], maxZoom: 16" in JS
    assert "fitForecastMapToFarm(true)" in JS
    assert "state.forecastMapFitKey = null" in JS
    assert "fitForecastMapToFarm();" in JS
