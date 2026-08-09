from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_v26_version_and_official_tool_icons():
    assert client.get("/api/health").json()["api_version"] == "2.11.0"
    brand = ROOT / "app/static/assets/brand"
    for name in (
        "weather-gis-icon.png",
        "weather-gis-icon-64.png",
        "weather-gis-icon-128.png",
        "coco-pilot-icon.png",
        "coco-pilot-icon-128.png",
    ):
        path = brand / name
        assert path.exists()
        assert path.stat().st_size > 1000


def test_liquid_glass_skin_preserves_main_structure_and_repairs_pest_panel():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert 'id="pestCardDeck"' in html
    assert 'id="pestHighestScore"' in html
    assert 'weather-gis-icon.png' in html
    assert 'coco-pilot-icon.png' in html
    assert "--glass-bg" in css
    assert "backdrop-filter: blur(var(--glass-blur))" in css
    assert "@supports not ((-webkit-backdrop-filter" in css
    assert ".pest-risk-head" in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(190px, 240px)" in css
    assert ".pest-card-deck > .empty-state" in css


def test_weather_gis_uses_official_icon_and_liquid_glass_skin():
    html = (ROOT / "app/static/weather-viewer/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/weather-viewer/styles.css").read_text(encoding="utf-8")
    assert "weather-gis-icon-64.png" in html
    assert "weather-gis-icon-128.png" in html
    assert "--glass-panel" in css
    assert "backdrop-filter: blur(24px)" in css
