from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_phase11_interface_status_endpoint() -> None:
    response = client.get("/api/v2/interface/status")
    assert response.status_code == 200
    body = response.json()
    assert body["interface_id"] == "v3.interface"
    assert body["availability"] == "available"
    assert body["theme"]["default"] == "official_white"
    assert body["theme"]["liquid_glass_enabled"] is False
    assert body["landing"]["interactive_coconut_hologram"] is True
    assert body["visualizations"]["chart_zoom"] is True
    assert body["audio"]["background_music_preserved"] is True


def test_phase11_static_assets_are_served() -> None:
    root = client.get("/")
    assert root.status_code == 200
    assert "/static/phase11.css" in root.text
    assert "/static/phase11.js" in root.text
    assert "coconutHologramPreview" not in root.text
    assert "coconutHologramWorkspace" in root.text
    assert "globalNavButton" in root.text
    assert "weather-gis-page" in root.text
    assert "Decision-support network" in root.text

    for path in (
        "/static/phase11.css",
        "/static/phase11.js",
        "/static/weather-viewer/phase11.css",
        "/static/weather-viewer/phase11.js",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.content


def test_phase11_coco_pilot_status_reports_official_report_generator() -> None:
    response = client.get("/api/v2/coco-pilot/status")
    assert response.status_code == 200
    assert response.json()["formal_report_generator_version"] == "formal-report-generator-1.1.0"
