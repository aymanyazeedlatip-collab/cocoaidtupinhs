from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from app.core.errors import EngineExecutionError
from app.domain.enums import DataQualityFlag
from app.domain.production import LegacyProductionFeatureSnapshot, LegacyVarietyClass, ProductionEngineRequest
from app.models.registry import load_model
from app.weather.assimilation import repository as weather_repository

PRODUCTION_FEATURE_ADAPTER_VERSION = "production-feature-adapter-1.0.0"
LEGACY_PRODUCTION_FEATURE_ORDER = [
    "farm_area_hectares", "productive_trees", "aging_trees", "stressed_trees",
    "infested_trees", "recovering_trees", "annual_rainfall_mm", "mean_temperature_c",
    "relative_humidity_percent", "drought_exposure", "weather_severity", "soil_ph",
    "nitrogen_index", "phosphorus_index", "potassium_index", "suitability_score",
    "pest_probability", "variety", "intervention",
]


def verify_artifact_feature_contract() -> None:
    artifact = load_model("production")
    if artifact is None:
        raise EngineExecutionError("The retained production model is unavailable")
    artifact_features = list(artifact.get("features", []))
    if artifact_features != LEGACY_PRODUCTION_FEATURE_ORDER:
        raise EngineExecutionError(
            "Production model feature schema does not match the frozen Phase 4 adapter",
            details={"artifact_features": artifact_features, "adapter_features": LEGACY_PRODUCTION_FEATURE_ORDER},
        )


def _feature_map(feature_set: dict[str, Any]) -> dict[str, float]:
    return {str(item["name"]): float(item["value"]) for item in feature_set.get("features", [])}


def _mean_temperature(weather_run: dict[str, Any]) -> tuple[float, list[DataQualityFlag], str]:
    values = weather_run.get("values", [])
    direct = [float(item["value"]) for item in values if item.get("value") is not None and item.get("variable") == "temperature_2m_mean" and item.get("period_kind") in {"historical", "current"}]
    if direct:
        return fmean(direct), [DataQualityFlag.REFERENCE_ONLY], "Mean daily temperature_2m_mean from archived forecast/history values."
    maxima: dict[str, float] = {}
    minima: dict[str, float] = {}
    for item in values:
        if item.get("value") is None or item.get("period_kind") not in {"historical", "current"}:
            continue
        if item.get("variable") == "temperature_2m_max":
            maxima[str(item["valid_at"])[:10]] = float(item["value"])
        elif item.get("variable") == "temperature_2m_min":
            minima[str(item["valid_at"])[:10]] = float(item["value"])
    shared = sorted(set(maxima) & set(minima))
    if shared:
        return fmean((maxima[day] + minima[day]) / 2 for day in shared), [DataQualityFlag.REFERENCE_ONLY], "Mean of daily maximum/minimum temperature midpoints from archived forecast/history values."
    current = [float(item["value"]) for item in values if item.get("value") is not None and item.get("variable") == "temperature_2m"]
    if current:
        return fmean(current), [DataQualityFlag.LOW_TEMPORAL_RESOLUTION], "Current temperature used because daily historical means were unavailable."
    raise EngineExecutionError("Weather run does not contain temperature values required by the production model")


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(upper, max(lower, float(value)))


def build_feature_snapshot(
    request: ProductionEngineRequest,
    *,
    database_path: Path | None = None,
) -> LegacyProductionFeatureSnapshot:
    verify_artifact_feature_contract()
    feature_set = weather_repository.get_feature_set(request.weather_feature_set_id, database_path=database_path)
    if not feature_set:
        raise EngineExecutionError(
            "Weather feature set not found",
            details={"weather_feature_set_id": str(request.weather_feature_set_id)},
        )
    weather_run = weather_repository.get_run(feature_set["weather_run_id"], include_values=True, database_path=database_path)
    if not weather_run:
        raise EngineExecutionError("Weather run linked to the feature set was not found")
    features = _feature_map(feature_set)
    warnings: list[str] = []
    quality_flags: list[DataQualityFlag] = [DataQualityFlag.REFERENCE_ONLY]

    rainfall_90 = features.get("rainfall_90d_mm")
    if rainfall_90 is not None:
        annual_rainfall = max(0.0, rainfall_90 * 365.0 / 90.0)
        rainfall_source = "Annualized rainfall_90d_mm from the Phase 3 weather feature set."
    elif "rainfall_30d_mm" in features:
        annual_rainfall = max(0.0, features["rainfall_30d_mm"] * 365.0 / 30.0)
        rainfall_source = "Annualized rainfall_30d_mm because the 90-day feature was unavailable."
        quality_flags.append(DataQualityFlag.LOW_TEMPORAL_RESOLUTION)
        warnings.append("Annual rainfall was extrapolated from a 30-day window.")
    else:
        raise EngineExecutionError("Weather feature set lacks rainfall_90d_mm and rainfall_30d_mm")

    mean_temperature, temperature_flags, temperature_source = _mean_temperature(weather_run)
    quality_flags.extend(temperature_flags)
    humidity = features.get("mean_relative_humidity_30d_percent")
    if humidity is None:
        raise EngineExecutionError("Weather feature set lacks mean_relative_humidity_30d_percent")
    dry_days = features.get("consecutive_dry_days", 0.0)
    moisture_30 = features.get("moisture_balance_30d_mm", 0.0)
    heat_days = features.get("forecast_heat_stress_days_16d", 0.0)
    max_gust = features.get("forecast_max_wind_gust_16d_kmh", 0.0)
    drought_exposure = _clamp(max(dry_days / 30.0, max(0.0, -moisture_30) / 150.0))
    weather_severity = _clamp(
        0.35 * drought_exposure
        + 0.25 * _clamp(heat_days / 16.0)
        + 0.25 * _clamp(max_gust / 120.0)
        + 0.15 * _clamp(max(0.0, -moisture_30) / 250.0)
    )

    variety = request.variety_class
    if variety == LegacyVarietyClass.UNKNOWN:
        variety = LegacyVarietyClass.TALL
        warnings.append("Unknown variety class was mapped to Tall for compatibility with the retained model.")
        quality_flags.append(DataQualityFlag.IMPUTED)

    row: dict[str, float | int | str] = {
        "farm_area_hectares": request.farm_area_hectares,
        "productive_trees": request.productive_trees,
        "aging_trees": request.aging_trees,
        "stressed_trees": request.stressed_trees,
        "infested_trees": request.infested_trees,
        "recovering_trees": request.recovering_trees,
        "annual_rainfall_mm": annual_rainfall,
        "mean_temperature_c": mean_temperature,
        "relative_humidity_percent": humidity,
        "drought_exposure": drought_exposure,
        "weather_severity": weather_severity,
        "soil_ph": request.soil_ph,
        "nitrogen_index": request.nitrogen_index,
        "phosphorus_index": request.phosphorus_index,
        "potassium_index": request.potassium_index,
        "suitability_score": request.suitability_score,
        "pest_probability": request.pest_probability,
        "variety": variety.value,
        "intervention": request.intervention.value,
    }
    ordered = [row[name] for name in LEGACY_PRODUCTION_FEATURE_ORDER]
    canonical = json.dumps(
        {"feature_order": LEGACY_PRODUCTION_FEATURE_ORDER, "ordered_values": ordered},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    source_map = {
        "annual_rainfall_mm": rainfall_source,
        "mean_temperature_c": temperature_source,
        "relative_humidity_percent": "mean_relative_humidity_30d_percent from the Phase 3 feature set.",
        "drought_exposure": "Derived from consecutive dry days and 30-day moisture deficit.",
        "weather_severity": "Composite of drought exposure, forecast heat days, wind gust, and moisture deficit.",
        "variety": "Named variety class when available; otherwise supplied legacy class.",
    }
    unique_flags = list(dict.fromkeys(quality_flags))
    return LegacyProductionFeatureSnapshot(
        weather_feature_set_id=request.weather_feature_set_id,
        weather_run_id=feature_set["weather_run_id"],
        feature_adapter_version=PRODUCTION_FEATURE_ADAPTER_VERSION,
        feature_order=LEGACY_PRODUCTION_FEATURE_ORDER,
        features=row,
        ordered_values=ordered,
        source_map=source_map,
        quality_flags=unique_flags,
        warnings=warnings,
        feature_sha256=hashlib.sha256(canonical).hexdigest(),
    )
