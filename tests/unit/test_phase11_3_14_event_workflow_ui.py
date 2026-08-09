from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
STATUS = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")


def test_release_version_1314_and_assets():
    assert "phase11-agritech-interface-1.3.23" in STATUS
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML


def test_selected_threat_uses_long_term_forecast_snapshot_renderer():
    assert 'id="hazardSnapshotMap"' in HTML
    assert 'id="hazardSnapshotDate"' in HTML
    assert 'id="openHazardInForecast"' in HTML
    assert "hazardRepresentativeForecastFrame" in JS
    assert "drawRainDataUrl(frame)" in JS
    assert "Exact Open-Meteo hourly frame used by Model Forecast" in JS
    assert "Exact COCOAID long-term modeled frame used by Model Forecast" in JS


def test_health_indicators_are_event_conditioned():
    assert "event_conditioned_probability" in JS
    assert "weatherPestAdjustment" in JS
    assert "eventAnnualRainfall" in JS
    assert "isDry" in JS and "isWet" in JS
    client = TestClient(app)
    base = {"prior_probability": 0.15, "symptoms": {}, "average_tree_age": 30}
    dry = client.post("/api/pest-risk/evaluate", json={**base, "rainfall_mm_month": 20, "humidity_percent": 52}).json()
    wet = client.post("/api/pest-risk/evaluate", json={**base, "rainfall_mm_month": 900, "humidity_percent": 96}).json()
    assert wet["posterior_probability"] > dry["posterior_probability"]
    soil = {"elevation_m": 100, "slope_degrees": 4, "soil_ph": 6.1, "nitrogen_index": .65, "phosphorus_index": .65, "potassium_index": .65, "drainage_index": .7}
    normal = client.post("/api/suitability/evaluate", json={"soil_terrain": soil, "annual_rainfall_mm": 2200, "mean_temperature_c": 27, "humidity_percent": 75, "drought_exposure": .05, "climate_stress": .1}).json()
    dry_suit = client.post("/api/suitability/evaluate", json={"soil_terrain": soil, "annual_rainfall_mm": 900, "mean_temperature_c": 35, "humidity_percent": 55, "drought_exposure": .9, "climate_stress": .9}).json()
    assert dry_suit["percentage"] < normal["percentage"] - 10


def test_rehabilitation_uses_square_grid_with_polygon_clip():
    assert "clipFarmPolygonToCell" in JS
    assert "L.polygon(clippedShape" in JS
    assert "rehabGridPane" in JS
    assert "pointInsidePolygon" in JS
    assert "pane.style.clipPath" not in JS
    assert "L.circle([cell.center.latitude" not in JS


def test_auto_phase9_phase10_api_and_ui_exist():
    client = TestClient(app)
    response = client.get("/api/v2/workflows/auto-phase9-10/status")
    assert response.status_code == 200
    body = response.json()
    assert "phase9" in body and "phase10" in body
    assert HTML.count("data-auto-workflow-status") >= 4
    assert "run_phase9_workflow.py" in (ROOT / "app/workflows/auto_phase_runner.py").read_text(encoding="utf-8")
    assert "run_phase10_workflow.py" in (ROOT / "app/workflows/auto_phase_runner.py").read_text(encoding="utf-8")
    assert "auto_phase_workflow_loop" in (ROOT / "launcher.py").read_text(encoding="utf-8")


def test_late_stage_pages_have_interactivity_and_motion():
    assert "interactive-network" in HTML
    assert 'id="networkLiveDetail"' in HTML
    assert "report-motion-pipeline" in HTML
    assert "database-live-rail" in HTML
    assert "interactive-formula-catalog" in HTML
    assert "networkNodePulse" in CSS
    assert "dbOrbit" in CSS
    assert "methodSweep" in CSS


def test_coco_pilot_hologram_has_four_runtime_states():
    assert 'id="pilotNcsHologram"' in HTML
    assert "pilot-ncs-hologram" in CSS
    for mode in ("waiting", "typing", "loading", "speaking"):
        assert mode in JS or mode in HTML
    assert "setPilotSphereState" in JS
    assert "pilotRingA" in CSS


def test_manual_phase_workflow_scripts_no_longer_require_pasted_ids():
    phase9 = (ROOT / "scripts/run_phase9_workflow.py").read_text(encoding="utf-8")
    phase10 = (ROOT / "scripts/run_phase10_workflow.py").read_text(encoding="utf-8")
    assert "input(" not in phase9
    assert "input(" not in phase10
    assert "/api/v2/pests/observations" in phase9
    assert "/api/v2/decision-support/runs?limit=1" in phase10
