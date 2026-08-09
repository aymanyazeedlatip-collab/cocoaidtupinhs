from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.weather import http as weather_http


class _FakeClient:
    calls: list[bool] = []
    direct_response: httpx.Response | None = None

    def __init__(self, *args, trust_env=True, **kwargs):
        self.trust_env = trust_env
        self.__class__.calls.append(trust_env)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        request = httpx.Request("GET", url, params=params)
        if self.trust_env:
            raise httpx.ConnectError("", request=request)
        if self.direct_response is None:
            raise httpx.ConnectError("", request=request)
        return self.direct_response


@pytest.fixture(autouse=True)
def resilience_settings(monkeypatch):
    monkeypatch.setattr(settings, "weather_request_attempts", 1)
    monkeypatch.setattr(settings, "weather_direct_connection_fallback", True)
    monkeypatch.setattr(settings, "weather_use_system_trust_store", False)
    _FakeClient.calls = []
    _FakeClient.direct_response = None


@pytest.mark.asyncio
async def test_blank_httpx_error_retries_without_environment_proxy(monkeypatch):
    request = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    _FakeClient.direct_response = httpx.Response(
        200,
        request=request,
        json={"current": {"temperature_2m": 30.0}},
    )
    monkeypatch.setattr(weather_http.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(weather_http.httpx, "AsyncHTTPTransport", lambda **kwargs: SimpleNamespace())

    result = await weather_http.get_json(
        "https://api.open-meteo.com/v1/forecast",
        {"latitude": 6.334, "longitude": 124.952},
    )

    assert result["current"]["temperature_2m"] == 30.0
    assert _FakeClient.calls == [True, False]


@pytest.mark.asyncio
async def test_total_network_failure_has_nonblank_diagnostics(monkeypatch):
    monkeypatch.setattr(weather_http.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(weather_http.httpx, "AsyncHTTPTransport", lambda **kwargs: SimpleNamespace())

    with pytest.raises(ProviderUnavailableError) as caught:
        await weather_http.get_json(
            "https://api.open-meteo.com/v1/forecast",
            {"latitude": 6.334, "longitude": 124.952},
        )

    error = caught.value
    assert "ConnectError" in error.message
    assert "No exception message" in error.message or "ConnectError" in error.message
    assert error.details["provider_host"] == "api.open-meteo.com"
    assert len(error.details["attempts"]) == 2
    assert {item["mode"] for item in error.details["attempts"]} == {"environment", "direct"}
    assert all(item["message"] for item in error.details["attempts"])


def test_exception_message_walks_nested_cause():
    inner = OSError("certificate verify failed")
    outer = httpx.ConnectError("")
    outer.__cause__ = inner
    assert "certificate verify failed" in weather_http._exception_message(outer)
