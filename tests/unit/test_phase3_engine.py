from __future__ import annotations

from app.domain.enums import EngineAvailability
from app.engines.registry import engine_registry
from app.engines.weather_assimilation import weather_assimilation_engine
from tests.weather_factory import RETRIEVED_AT, make_open_meteo_payload


def test_weather_assimilation_engine_is_registered_and_executable():
    descriptor = engine_registry.descriptor("v3.weather_assimilation")
    assert descriptor.availability == EngineAvailability.AVAILABLE
    assert descriptor.version == "1.0.0"

    result = weather_assimilation_engine.execute({
        "provider_payload": make_open_meteo_payload(),
        "provider_model": "auto",
        "forecast_days": 16,
        "history_days": 90,
        "retrieved_at": RETRIEVED_AT,
    })
    assert result.engine_id == "v3.weather_assimilation"
    assert result.output.feature_adapter_version == "weather-features-1.0.0"
    assert len(result.output.features) == 14
    assert any("archived forecast" in warning for warning in result.warnings)
