from __future__ import annotations

from app.domain.enums import EngineAvailability, EngineMaturity
from app.domain.weather import WeatherAssimilationPayload, WeatherFeatureSet
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.engines.registry import engine_registry
from app.weather.assimilation.features import FEATURE_ADAPTER_VERSION, build_weather_feature_set
from app.weather.assimilation.normalizer import normalize_open_meteo_payload


WEATHER_ASSIMILATION_DESCRIPTOR = EngineDescriptor(
    engine_id="v3.weather_assimilation",
    name="Weather Assimilation Engine",
    version="1.0.0",
    maturity=EngineMaturity.EXPERIMENTAL,
    availability=EngineAvailability.AVAILABLE,
    input_contract="WeatherAssimilationPayload",
    output_contract="WeatherFeatureSet",
    dependencies=["open_meteo_forecast_api", "weather_run_repository"],
    limitations=[
        "Past-day values from the Forecast API are archived forecasts, not field observations.",
        "The seamless Open-Meteo endpoint does not expose one authoritative provider initialization time.",
        "Long-term climate-conditioned scenarios are intentionally outside this engine.",
    ],
)


class WeatherAssimilationEngine(AnalyticalEngine[WeatherAssimilationPayload, WeatherFeatureSet]):
    descriptor = WEATHER_ASSIMILATION_DESCRIPTOR
    input_model = WeatherAssimilationPayload
    output_model = WeatherFeatureSet

    def _run(
        self,
        payload: WeatherAssimilationPayload,
        context: EngineExecutionContext,
    ) -> tuple[WeatherFeatureSet, list[str]]:
        normalized = normalize_open_meteo_payload(
            payload.provider_payload,
            model=payload.provider_model,
            forecast_days=payload.forecast_days,
            history_days=payload.history_days,
            retrieved_at=payload.retrieved_at,
        )
        feature_set = build_weather_feature_set(normalized, farm_id=payload.farm_id)
        warnings: list[str] = []
        if normalized.is_stale:
            warnings.append("A stale cached weather run was used because the live provider was unavailable.")
        if payload.history_days:
            warnings.append(
                "Lagged features use archived forecast values supplied through Open-Meteo past_days; they are not measured observations."
            )
        return feature_set, warnings


weather_assimilation_engine = WeatherAssimilationEngine()
engine_registry.register(weather_assimilation_engine)

__all__ = [
    "FEATURE_ADAPTER_VERSION",
    "WEATHER_ASSIMILATION_DESCRIPTOR",
    "WeatherAssimilationEngine",
    "weather_assimilation_engine",
]
