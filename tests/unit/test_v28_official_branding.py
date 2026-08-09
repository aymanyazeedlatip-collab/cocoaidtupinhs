from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
WEATHER_HTML = (ROOT / "app" / "static" / "weather-viewer" / "index.html").read_text(encoding="utf-8")


def test_v28_version_and_official_brand_assets():
    client = TestClient(app)
    assert client.get("/api/health").json()["api_version"] == "2.11.0"
    for asset in [
        "/static/assets/brand/coco-aid-logo.png",
        "/static/assets/brand/coco-aid-logo-192.png",
        "/static/assets/brand/coco-aid-wordmark.png",
        "/static/assets/brand/coco-aid-official-lockup.png",
        "/static/assets/brand/coco-aid-favicon.png",
    ]:
        response = client.get(asset)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")


def test_official_branding_is_used_across_interfaces():
    assert HTML.count('/static/assets/brand/coco-aid-logo') >= 2
    assert HTML.count('/static/assets/brand/coco-aid-wordmark.png') >= 2
    assert '/static/assets/brand/coco-aid-official-lockup.png' in HTML
    assert '/static/assets/brand/coco-aid-wordmark.png' in WEATHER_HTML
