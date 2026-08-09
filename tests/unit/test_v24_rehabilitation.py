from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.farm import FarmCreate
from app.services import assistant as assistant_service

client = TestClient(app)


def _hazard(event_type="typhoon", severity=0.82, loss=36.0):
    return {
        "event_type": event_type,
        "label": "Projected severe weather event",
        "start_date": "2030-08-01",
        "end_date": "2030-08-05",
        "peak_severity": severity,
        "estimated_production_loss_tons": 2.4,
        "loss_percent_of_event_baseline": loss,
        "estimated_trees_affected": 120,
        "data_mode": "plausible_stochastic_climate_simulation",
        "confidence": "Scenario-dependent estimate",
    }


def test_event_rehabilitation_plan_has_dates_heatmap_and_three_classes():
    farm = FarmCreate()
    response = client.post("/api/rehabilitation-plan", json={
        "farm": farm.model_dump(mode="json"),
        "hazards": [_hazard()],
        "rows": 14,
        "cols": 14,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["rows"] == 14 and data["cols"] == 14
    assert len(data["plans"]) == 1
    plan = data["plans"][0]
    assert plan["recommended_assessment_date"] == "2030-08-08"
    assert plan["recommended_rehabilitation_date"] == "2030-08-12"
    assert len(plan["cells"]) >= 100
    assert sum(plan["counts"].values()) == len(plan["cells"])
    assert plan["counts"]["Needs Rehabilitation"] > 0
    assert plan["procedure"]
    assert "Field inspection" in data["warning"]


def test_multiple_hazards_generate_multiple_rehabilitation_maps():
    farm = FarmCreate()
    response = client.post("/api/rehabilitation-plan", json={
        "farm": farm.model_dump(mode="json"),
        "hazards": [
            _hazard("typhoon", 0.8, 35),
            {**_hazard("drought", 0.55, 18), "start_date": "2032-02-01", "end_date": "2032-03-15"},
            {**_hazard("extreme_rain", 0.7, 28), "start_date": "2034-10-03", "end_date": "2034-10-12"},
        ],
        "rows": 12,
        "cols": 12,
    })
    assert response.status_code == 200
    plans = response.json()["plans"]
    assert len(plans) == 3
    assert [p["event_type"] for p in plans] == ["typhoon", "drought", "extreme_rain"]
    assert all(p["recommended_rehabilitation_date"] > p["event_end_date"] for p in plans)


def test_frontend_rehabilitation_heatmap_and_ai_contract():
    html = client.get("/").text
    js = client.get("/static/app.js").text
    css = client.get("/static/styles.css").text
    for identifier in ("rehabEventStrip", "rehabSchedule", "generateRehabAiButton", "rehabAiResult"):
        assert f'id="{identifier}"' in html
    assert 'api("/api/rehabilitation-plan"' in js
    assert "function generateRehabAiRecommendation" in js
    assert "rehabHeatColor" in js
    assert ".rehab-heat-blob" in css
    assert "Green · No Damage" in html
    assert "Yellow · Needs inspection" in html
    assert "Red · Needs Rehabilitation" in html


def test_automatic_flash_model_fallback(monkeypatch, tmp_path):
    private_file = tmp_path / "private.json"
    private_file.write_text('{"gemini_api_key":"AIza' + 'x' * 36 + '"}', encoding="utf-8")
    monkeypatch.setattr(assistant_service, "_PRIVATE_FILE", private_file)
    monkeypatch.setattr(assistant_service.settings, "gemini_api_key", None)
    monkeypatch.setattr(assistant_service.settings, "gemini_model", "gemini-2.5-flash")

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)
        def json(self):
            return self._payload

    called = []
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, endpoint, *args, **kwargs):
            called.append(endpoint)
            if "gemini-2.5-flash" in endpoint:
                return FakeResponse(404, {"error": {"message": "Model is not available"}})
            return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "Use field inspection first."}]}}]})

    monkeypatch.setattr(assistant_service.httpx, "AsyncClient", FakeClient)
    response = client.post("/api/assistant/chat", json={
        "message": "Prepare a rehabilitation plan.",
        "history": [],
        "document_ids": [],
    })
    assert response.status_code == 200
    assert response.json()["model"] == "Automatic compatible Flash model"
    assert any("gemini-2.5-flash" in endpoint for endpoint in called)
    assert any("gemini-flash-latest" in endpoint for endpoint in called)


def test_moderate_loss_event_creates_inspection_zones_not_false_all_green():
    farm = FarmCreate()
    moderate = _hazard("drought", 0.30, 14.0)
    response = client.post("/api/rehabilitation-plan", json={
        "farm": farm.model_dump(mode="json"),
        "hazards": [moderate],
        "rows": 14,
        "cols": 14,
    })
    assert response.status_code == 200
    counts = response.json()["plans"][0]["counts"]
    assert counts["Needs inspection"] + counts["Needs Rehabilitation"] > 0
