from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.errors import ProviderRateLimitError, ProviderUnavailableError
from app.schemas.weather import WeatherPointRequest
from app.services.cache import cache
from app.weather import providers
from tests.weather_factory import make_open_meteo_payload


def _request() -> WeatherPointRequest:
    return WeatherPointRequest(
        latitude=6.334, longitude=124.952, model="auto", forecast_days=16, past_days=90,
    )


def _key(request: WeatherPointRequest) -> str:
    return (
        f"weather-point-v3:{request.latitude:.3f}:{request.longitude:.3f}:{request.model}:"
        f"f{request.forecast_days}:p{request.past_days}"
    )


@pytest.fixture(autouse=True)
def reset_weather_provider_state(monkeypatch):
    cache._items.clear()
    providers._provider_cooldown_until = 0.0
    monkeypatch.setattr(settings, "offline_mode", False)
    monkeypatch.setattr(providers.persistent_cache, "get", lambda *args, **kwargs: None)
    monkeypatch.setattr(providers.persistent_cache, "set", lambda *args, **kwargs: None)
    yield
    cache._items.clear()
    providers._provider_cooldown_until = 0.0


@pytest.mark.asyncio
async def test_provider_requests_exact_history_and_sixteen_day_horizon(monkeypatch):
    captured = {}

    async def fake_get_json(url, params):
        captured["url"] = url
        captured["params"] = params
        return make_open_meteo_payload()

    monkeypatch.setattr(providers, "get_json", fake_get_json)
    result = await providers.fetch_point_forecast(_request())

    assert captured["params"]["forecast_days"] == 16
    assert captured["params"]["past_days"] == 90
    assert "vapour_pressure_deficit" in captured["params"]["hourly"]
    assert "soil_moisture_0_to_1cm" in captured["params"]["hourly"]
    assert "shortwave_radiation_sum" in captured["params"]["daily"]
    assert "relative_humidity_2m_mean" not in captured["params"]["daily"]
    assert "vapour_pressure_deficit_max" not in captured["params"]["daily"]
    assert result["metadata"]["forecast_horizon_days"] == 16
    assert result["metadata"]["past_days_requested"] == 90


@pytest.mark.asyncio
async def test_rate_limit_uses_stale_cache_and_activates_cooldown(monkeypatch):
    request = _request()
    stale = make_open_meteo_payload()
    cache.set(_key(request), stale, 0)

    async def rate_limited(*args, **kwargs):
        raise ProviderRateLimitError("test 429")

    monkeypatch.setattr(providers, "get_json", rate_limited)
    result = await providers.fetch_point_forecast(request)
    assert result["metadata"]["is_stale"] is True
    assert providers._cooldown_remaining() > 0


@pytest.mark.asyncio
async def test_offline_mode_uses_cache_when_available(monkeypatch):
    request = _request()
    cache.set(_key(request), make_open_meteo_payload(), 0)
    monkeypatch.setattr(settings, "offline_mode", True)

    result = await providers.fetch_point_forecast(request)
    assert result["metadata"]["is_stale"] is True
    assert result["metadata"]["offline_cache"] is True


@pytest.mark.asyncio
async def test_offline_mode_without_cache_fails_clearly(monkeypatch):
    monkeypatch.setattr(settings, "offline_mode", True)
    with pytest.raises(ProviderUnavailableError, match="no cached forecast"):
        await providers.fetch_point_forecast(_request())

@pytest.mark.asyncio
async def test_offline_mode_discloses_fresh_persistent_cache(monkeypatch):
    payload = make_open_meteo_payload()
    payload["metadata"] = {
        "retrieved_at": "2026-08-03T05:30:00+00:00",
        "forecast_horizon_days": 16,
        "past_days_requested": 90,
        "is_stale": False,
    }
    monkeypatch.setattr(providers.persistent_cache, "get", lambda *args, **kwargs: payload)
    monkeypatch.setattr(settings, "offline_mode", True)

    result = await providers.fetch_point_forecast(_request())
    assert result["metadata"]["offline_cache"] is True
    assert result["metadata"]["served_from_cache"] is True
    assert result["metadata"]["live_provider_contacted"] is False
    assert result["metadata"]["is_stale"] is False
    assert result["metadata"]["retrieved_at"] == "2026-08-03T05:30:00+00:00"
    assert result["metadata"]["forecast_horizon_days"] == 16
