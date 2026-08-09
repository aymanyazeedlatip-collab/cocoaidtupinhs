from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import assistant as assistant_service

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def _configure_private(monkeypatch, tmp_path):
    private = tmp_path / "private.json"
    private.write_text('{"gemini_api_key":"AIza' + 'x' * 36 + '"}', encoding="utf-8")
    monkeypatch.setattr(assistant_service, "_PRIVATE_FILE", private)
    monkeypatch.setattr(assistant_service.settings, "gemini_api_key", None)
    monkeypatch.setattr(assistant_service.settings, "gemini_model", "gemini-flash-latest")
    return private


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_assistant_retries_provider_500_and_returns_clear_answer(monkeypatch, tmp_path):
    _configure_private(monkeypatch, tmp_path)
    calls = []

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def post(self, endpoint, *args, **kwargs):
            calls.append(endpoint)
            if len(calls) < 3:
                return FakeResponse(500, {"error": {"message": "temporary backend error"}})
            return FakeResponse(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "Inspect the palms and record visible damage."}]}}]})

    monkeypatch.setattr(assistant_service.httpx, "AsyncClient", FakeClient)
    response = client.post("/api/assistant/chat", json={"message": "What should I inspect?", "history": [], "document_ids": []})
    assert response.status_code == 200
    assert "Inspect the palms" in response.json()["answer"]
    assert len(calls) == 3


def test_assistant_continues_max_token_response(monkeypatch, tmp_path):
    _configure_private(monkeypatch, tmp_path)
    payloads = []

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def post(self, endpoint, *args, **kwargs):
            payloads.append(kwargs["json"])
            if len(payloads) == 1:
                return FakeResponse(200, {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "Start by inspecting drainage."}]}}]})
            return FakeResponse(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "Then document affected palms and schedule follow-up."}]}}]})

    monkeypatch.setattr(assistant_service.httpx, "AsyncClient", FakeClient)
    response = client.post("/api/assistant/chat", json={"message": "Give me a procedure.", "history": [], "document_ids": []})
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "Start by inspecting" in answer
    assert "schedule follow-up" in answer
    assert len(payloads) == 2


def test_assistant_ui_has_loading_dots_and_rehabilitation_arrows():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert 'id="rehabPrevEvent"' in html
    assert 'id="rehabNextEvent"' in html
    assert "function changeRehabPlan" in js
    assert "function appendPilotLoading" in js
    assert "pilot-typing-dots" in js
    assert "@keyframes pilotDotBounce" in css


def test_project_has_no_explicit_gemini_35_reference():
    excluded = {".venv", "__pycache__", ".pytest_cache"}
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".js", ".html", ".css", ".md", ".example", ".bat"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        blocked = ("gemini " + "3" + ".5", "gemini-" + "3" + ".5")
        if any(term in text for term in blocked):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_assistant_provider_failure_returns_503_not_internal_500(monkeypatch, tmp_path):
    _configure_private(monkeypatch, tmp_path)
    monkeypatch.setattr(assistant_service, "_MODEL_FALLBACKS", ("gemini-flash-latest",))

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def post(self, endpoint, *args, **kwargs):
            return FakeResponse(500, {"error": {"message": "temporary provider failure"}})

    async def no_wait(_):
        return None

    monkeypatch.setattr(assistant_service.httpx, "AsyncClient", FakeClient)
    import asyncio
    monkeypatch.setattr(asyncio, "sleep", no_wait)
    response = client.post("/api/assistant/chat", json={"message": "Help me inspect my farm.", "history": [], "document_ids": []})
    assert response.status_code == 503
    assert response.status_code != 500
    assert "usable response" in response.json()["detail"].lower()
