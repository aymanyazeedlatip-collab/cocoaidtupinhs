from pathlib import Path

from fastapi.testclient import TestClient

import app.api.v2.routes as routes
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HJS = (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
STATUS = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")


def test_release_1315_and_mature_hologram():
    assert "phase11-agritech-interface-1.3.23" in STATUS
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML
    assert "white_mature_coconut_mesh" in STATUS
    assert "mature_coconut_scale" in STATUS
    assert "spherical_mature_coconut_geometry" in STATUS
    assert "const shoulder = .955" in HJS
    assert 'const coconut = makeModel("coconut", .94);' in HJS
    assert 'context.strokeStyle = `rgba(255,255,255,' in HJS
    assert 'data-hologram-start-offset-ms="0"' in HTML


def test_rehab_grid_is_geometrically_clipped_not_pane_masked():
    assert "clipFarmPolygonToCell" in JS
    assert "const clippedShape" in JS
    assert "L.polygon(clippedShape" in JS
    assert "updateRehabGridClip" not in JS
    assert "pane.style.clipPath" not in JS
    assert "L.circle([cell.center.latitude" not in JS


def test_forecast_immediately_bootstraps_auto_phase_workflow():
    assert "triggerAutomaticPhaseWorkflows(payload.farm)" in JS
    assert "/api/v2/workflows/auto-phase9-10/bootstrap" in JS
    assert "bootstrap_from_farm" in (ROOT / "app/workflows/auto_phase_runner.py").read_text(encoding="utf-8")
    assert "/workflows/auto-phase9-10/bootstrap" in (ROOT / "app/api/v2/routes.py").read_text(encoding="utf-8")


def test_bootstrap_endpoint_accepts_current_farm(monkeypatch):
    async def fake_bootstrap(farm, base_url):
        return {
            "farm_id": "11111111-1111-4111-8111-111111111111",
            "production_forecast_id": "22222222-2222-4222-8222-222222222222",
            "workflow": {"state": "running", "phase9": "Running", "phase10": "Waiting", "message": "started"},
        }

    monkeypatch.setattr(routes, "bootstrap_from_farm", fake_bootstrap)
    payload = {
        "name": "Test Farm",
        "location": {"region": "Region XII", "province": "South Cotabato", "municipality": "Tupi", "barangay": "Palian", "latitude": 6.334, "longitude": 124.952, "polygon": []},
        "area_hectares": 5,
        "trees": {"total_trees": 10, "young": 1, "productive": 6, "aging": 1, "stressed": 1, "infested": 0, "recovering": 1, "dead": 0, "average_age_years": 25, "variety": "Tall"},
        "production": {"annual_production_tons": 12, "yield_tons_per_hectare": 2.4},
        "soil_terrain": {"elevation_m": 100, "slope_degrees": 4, "soil_ph": 6.1, "nitrogen_index": .6, "phosphorus_index": .6, "potassium_index": .6, "drainage_index": .7},
        "symptoms": {"severity": 0}, "management": {}, "events": [], "provenance": {},
    }
    response = TestClient(app).post("/api/v2/workflows/auto-phase9-10/bootstrap", json=payload)
    assert response.status_code == 200
    assert response.json()["workflow"]["phase9"] == "Running"


def test_arrow_controls_and_pilot_ui_are_visually_emphasized():
    assert "button[aria-label*=" in CSS
    assert "background:linear-gradient(145deg,#fff8ee,#ffe8ca)" in CSS
    assert "pilotWholeSphereFloat" in CSS
    assert "width:min(480px" in CSS
    assert "pilot-message.assistant" in CSS
