from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_v25_version_and_brand_assets_exist():
    assert client.get("/api/health").json()["api_version"] == "2.11.0"
    assets = ROOT / "app" / "static" / "assets" / "brand"
    for name in (
        "coconut-farm-hero.jpg",
        "coco-aid-wordmark.png",
        "coco-aid-logo.png",
        "coco-aid-logo-192.png",
        "coco-aid-favicon.png",
    ):
        path = assets / name
        assert path.exists()
        assert path.stat().st_size > 1000


def test_final_ui_has_wordmark_farm_background_about_page_and_loading_experience():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert '/static/assets/brand/coco-aid-wordmark.png' in html
    assert '/static/assets/brand/coco-aid-logo.png' in html
    assert 'id="about"' in html
    assert 'Gavrielle Munoz' in html
    assert 'Tupi National High School' in html
    assert 'id="loadingTip"' in html
    assert 'id="loadingProgressBar"' not in html
    assert 'loading-wordmark' not in html.split('id="loadingOverlay"', 1)[1]
    assert "coconut-farm-hero.jpg" in css
    assert "slowLogoSpin" in css
    assert "loadingSweep" in css
    assert "LOADING_TIPS" in js
    assert 'about: ["About COCO-AID", "Research platform, methodology, evidence, and system scope"]' in js


def test_weather_viewer_uses_same_brand_identity():
    html = (ROOT / "app/static/weather-viewer/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/weather-viewer/styles.css").read_text(encoding="utf-8")
    assert '/static/assets/brand/weather-gis-icon-128.png' in html
    assert '/static/assets/brand/coco-aid-wordmark.png' in html
    assert '.brand-logo' in css
    assert '.brand-wordmark' in css
