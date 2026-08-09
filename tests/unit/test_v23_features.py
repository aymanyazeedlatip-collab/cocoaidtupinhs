from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from app.main import app
from app.services import assistant as assistant_service

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def test_health_version_and_playback_contract():
    assert client.get("/api/health").json()["api_version"] == "2.11.0"
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "const intervalMs = 500" in js
    assert "1 second = 2 days" in html
    assert 'id="forecastWindCanvas"' in html


def test_weather_viewer_is_one_shared_iframe_between_home_and_popup():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert html.count('id="weatherViewerFrame"') == 1
    assert 'id="weatherHomeMount"' in html
    assert 'id="weatherModalMount"' in html
    assert "mount.appendChild(frame)" in js
    assert "COCO_AID_RESIZE" in js


def test_draw_tutorial_and_rehab_map_framing_contract():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'id="drawTutorial"' in html
    assert "function startDrawTutorial" in js
    assert 'fitBounds(farmBounds' in js
    assert 'padding:[34,34]' in js


def test_coco_pilot_key_configuration_and_mocked_chat(monkeypatch, tmp_path):
    private_file = tmp_path / "private.json"
    monkeypatch.setattr(assistant_service, "_PRIVATE_FILE", private_file)
    monkeypatch.setattr(assistant_service.settings, "gemini_api_key", None)
    assert client.get("/api/assistant/status").json()["configured"] is False
    configured = client.post("/api/assistant/configure", json={"api_key": "AIza" + "x" * 36})
    assert configured.status_code == 200
    assert configured.json()["configured"] is True

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "Pest risk is **42%**.\n- Inspect lower fronds.\n- Record damage."}]}}]}

    call = {}
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            call.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr(assistant_service.httpx, "AsyncClient", FakeClient)
    response = client.post("/api/assistant/chat", json={
        "message": "What should I do?", "history": [], "context": {"farm": {"name": "Test"}}, "document_ids": []
    })
    assert response.status_code == 200
    assert response.json()["percentages"] == [42.0]
    assert call["headers"]["x-goog-api-key"].startswith("AIza")
    assert "params" not in call
    client.delete("/api/assistant/configure")


def test_assistant_can_extract_uploaded_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(assistant_service, "_DOC_DIR", tmp_path / "docs")
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.drawString(72, 720, "COCO-AID farm report: projected recovery probability is 63 percent.")
    pdf.save()
    response = client.post(
        "/api/assistant/upload-document",
        files={"file": ("farm-report.pdf", buf.getvalue(), "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "PDF"
    assert body["characters"] > 20


def test_pdf_contains_farm_location_shape_section():
    from app.schemas.farm import FarmCreate
    farm = FarmCreate()
    farm.location.polygon = [[6.33, 124.95], [6.34, 124.95], [6.34, 124.96], [6.33, 124.96]]
    analysis = client.post("/api/analysis/full", json={"farm": farm.model_dump(mode="json"), "runs": 100, "end_year": 2027}).json()
    forecast = client.post("/api/farm-site/forecast", json={
        "farm": farm.model_dump(mode="json"), "start_year": 2026, "end_year": 2027,
        "start_date": "2026-07-20", "runs": 100, "include_live_short_term": False,
    }).json()
    generated = client.post("/api/reports/generate", json={
        "analysis_id": analysis["analysis_id"], "analysis": {"farm_site_forecast": forecast}, "report_format": "pdf"
    })
    assert generated.status_code == 200
    content = client.get(generated.json()["download_url"]).content
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    assert "Farm Location, Shape, and Data Quality" in text
    assert "Farm centroid and entered boundary shape" in text
