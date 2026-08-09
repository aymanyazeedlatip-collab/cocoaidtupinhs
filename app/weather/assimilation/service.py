from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.weather import WeatherFeatureSet
from app.schemas.weather import WeatherPointRequest
from app.schemas.weather_assimilation import WeatherAssimilationRequest
from app.weather.assimilation.features import build_weather_feature_set
from app.weather.assimilation.normalizer import live_only_payload, normalize_open_meteo_payload
from app.weather.assimilation.repository import get_feature_set_for_run, get_run, save_run

logger = logging.getLogger(__name__)


async def assimilate_weather(request: WeatherAssimilationRequest) -> dict[str, Any]:
    from app.weather.providers import fetch_point_forecast

    provider_request = WeatherPointRequest(
        latitude=request.latitude,
        longitude=request.longitude,
        model=request.model,
        forecast_days=request.forecast_days,
        past_days=request.history_days,
    )
    payload = await fetch_point_forecast(provider_request, force_refresh=request.force_refresh)
    normalized = normalize_open_meteo_payload(
        payload,
        model=request.model,
        forecast_days=request.forecast_days,
        history_days=request.history_days,
    )
    feature_set = build_weather_feature_set(normalized, farm_id=request.farm_id)
    run_id, feature_set_id, reused = save_run(normalized, feature_set)
    run = get_run(run_id)
    features = get_feature_set_for_run(run_id)
    live_payload = live_only_payload(payload, forecast_days=request.forecast_days, retrieved_at=normalized.retrieved_at)
    live_payload.setdefault("metadata", {})["weather_run_id"] = run_id
    live_payload["metadata"]["feature_set_id"] = feature_set_id
    live_payload["metadata"]["feature_adapter_version"] = feature_set.feature_adapter_version
    live_payload["metadata"]["historical_feature_basis"] = normalized.provider_metadata["history_basis"]
    return {
        "weather_run": run,
        "feature_set": features,
        "reused_existing_run": reused,
        "live_forecast": live_payload,
        "separation_notice": {
            "live_weather": "Current conditions and at most 16 days of numerical forecast.",
            "history": "Past-day provider values are used only for lagged agricultural features and are not shown as future forecasts.",
            "long_term": "Conditions beyond Day 16 belong to Climate-Conditioned Farm Simulation and are not included here.",
        },
    }


def record_live_point_payload(payload: dict[str, Any], request: WeatherPointRequest) -> dict[str, Any]:
    """Best-effort persistence for the legacy Weather GIS without breaking its response contract."""
    try:
        normalized = normalize_open_meteo_payload(
            payload, model=request.model, forecast_days=request.forecast_days, history_days=request.past_days,
        )
        feature_set: WeatherFeatureSet | None = None
        if request.past_days >= 7:
            feature_set = build_weather_feature_set(normalized, farm_id=None)
        run_id, feature_set_id, reused = save_run(normalized, feature_set)
        result = live_only_payload(payload, forecast_days=request.forecast_days, retrieved_at=normalized.retrieved_at)
        result.setdefault("metadata", {})["weather_run_id"] = run_id
        result["metadata"]["feature_set_id"] = feature_set_id
        result["metadata"]["reused_existing_run"] = reused
        return result
    except Exception:
        logger.exception("Could not persist the live weather point run; returning provider data without a run identifier")
        return live_only_payload(payload, forecast_days=request.forecast_days)
