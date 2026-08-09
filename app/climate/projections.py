from __future__ import annotations

import math
import hashlib
import calendar
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import settings
from app.schemas.analysis import ClimateProjectionRequest, ClimateTrajectoryRequest

SCENARIO_STRENGTH = {"ssp126": 0.45, "ssp245": 0.75, "ssp370": 1.05, "ssp585": 1.35}
PERIOD_MIDPOINT = {"historical": 2000, "2021-2040": 2030, "2041-2060": 2050, "2061-2080": 2070, "2081-2100": 2090}


@lru_cache(maxsize=1)
def load_climate_demo() -> pd.DataFrame:
    if not settings.climate_demo_path.exists():
        from scripts.prepare_climate_demo import create_climate_demo
        create_climate_demo(settings.climate_demo_path)
    return pd.read_csv(settings.climate_demo_path)


def _nearest_location(df: pd.DataFrame, lat: float, lon: float) -> str:
    locs = df[["location_id", "latitude", "longitude"]].drop_duplicates().copy()
    distance = (locs["latitude"] - lat) ** 2 + ((locs["longitude"] - lon) * np.cos(np.radians(lat))) ** 2
    return str(locs.iloc[int(distance.argmin())]["location_id"])


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def climate_projection(request: ClimateProjectionRequest) -> dict[str, Any]:
    df = load_climate_demo()
    location_id = _nearest_location(df, request.latitude, request.longitude)
    subset = df[(df.location_id == location_id) & (df.scenario == request.scenario) & (df.period == request.period)].copy()
    if subset.empty:
        raise ValueError("climate projection not found")

    multiplier = {"multi_model_median": 0.0, "lower": -1.0, "upper": 1.0, "sample": 0.0}[request.model_mode]
    if request.model_mode in {"lower", "upper"}:
        delta = multiplier * subset["temperature_spread_c"]
        for field in ("mean_temperature_c", "minimum_temperature_c", "maximum_temperature_c"):
            subset[field] += delta
        subset["precipitation_mm"] *= np.clip(1 + multiplier * subset["precipitation_spread_fraction"], 0.2, 2.0)
    elif request.model_mode == "sample":
        seed_text = f"{request.latitude:.5f}|{request.longitude:.5f}|{request.scenario}|{request.period}"
        seed = int.from_bytes(hashlib.sha256(seed_text.encode()).digest()[:8], "big")
        rng = np.random.default_rng(seed)
        temperature_delta = rng.normal(0, subset["temperature_spread_c"].values)
        for field in ("mean_temperature_c", "minimum_temperature_c", "maximum_temperature_c"):
            subset[field] += temperature_delta
        subset["precipitation_mm"] *= np.clip(1 + rng.normal(0, subset["precipitation_spread_fraction"].values), 0.4, 1.8)
    subset["precipitation_mm"] = np.maximum(0, subset["precipitation_mm"])

    monthly = []
    for row in subset.sort_values("month").itertuples():
        monthly.append({
            "month": int(row.month),
            "precipitation_mm": round(float(row.precipitation_mm), 1),
            "mean_temperature_c": round(float(row.mean_temperature_c), 2),
            "minimum_temperature_c": round(float(row.minimum_temperature_c), 2),
            "maximum_temperature_c": round(float(row.maximum_temperature_c), 2),
            "relative_humidity_percent": round(float(row.relative_humidity_percent), 1),
            "wind_speed_ms": round(float(row.wind_speed_ms), 2),
            "consecutive_dry_days_index": round(float(row.consecutive_dry_days_index), 2),
            "heavy_rain_days": round(float(row.heavy_rain_days), 2),
            "heat_stress_days": round(float(row.heat_stress_days), 2),
            "drought_tendency": round(float(row.drought_tendency), 3),
            "coconut_climate_suitability": round(float(row.coconut_climate_suitability), 3),
        })

    source_row = subset.iloc[0]
    reference_distance_km = _distance_km(request.latitude, request.longitude, float(source_row.latitude), float(source_row.longitude))
    weighted_temperature = sum(
        m["mean_temperature_c"] * calendar.monthrange(2001, m["month"])[1] for m in monthly
    ) / 365
    distance_warning = (
        f"The nearest bundled reference location is {reference_distance_km:.0f} km away; the result is an extrapolative demonstration."
        if reference_distance_km > 250 else None
    )
    return {
        "location_id": location_id,
        "requested_coordinate": {"latitude": request.latitude, "longitude": request.longitude},
        "reference_coordinate": {"latitude": float(source_row.latitude), "longitude": float(source_row.longitude)},
        "reference_distance_km": round(reference_distance_km, 1),
        "scenario": request.scenario,
        "period": request.period,
        "display_label": "Historical reference period" if request.period == "historical" else ("2041–2060 projected climate period" if request.period == "2041-2060" else f"{request.period} projected climate period"),
        "model_mode": request.model_mode,
        "monthly": monthly,
        "annual_summary": {
            "annual_precipitation_mm": round(sum(m["precipitation_mm"] for m in monthly), 1),
            "mean_temperature_c": round(float(weighted_temperature), 2),
            "mean_drought_tendency": round(float(np.mean([m["drought_tendency"] for m in monthly])), 3),
            "mean_climate_suitability": round(float(np.mean([m["coconut_climate_suitability"] for m in monthly])), 3),
        },
        "data_source_type": "synthetic_reference_based",
        "source_basis": "Compact development projection shaped after CMIP6/WorldClim period and SSP conventions.",
        "warning": "This bundled projection is a lightweight development dataset, not downloaded farm-level CMIP6 output.",
        "distance_warning": distance_warning,
        "limitations": [
            "The values demonstrate climate-conditioned simulation and require replacement with processed NEX-GDDP-CMIP6 or WorldClim data.",
            "A climate period is a distribution of possible conditions, not an exact daily weather forecast.",
        ],
    }


def year_climate_parameters(year: int, scenario: str, latitude: float = 6.3) -> dict[str, float]:
    strength = SCENARIO_STRENGTH[scenario]
    progress = np.clip((year - 2020) / 80, 0, 1)
    temperature_anomaly = strength * 2.2 * progress
    rainfall_ratio = 1 + (0.025 * math.sin((year - 2020) / 4) - 0.035 * strength * progress)
    drought_probability = np.clip(0.10 + 0.10 * strength * progress, 0.05, 0.35)
    extreme_rain_probability = np.clip(0.10 + 0.045 * strength * progress, 0.05, 0.25)
    heat_probability = np.clip(0.08 + 0.16 * strength * progress, 0.04, 0.35)
    # Typhoon exposure is kept stationary across SSPs because future frequency changes are uncertain.
    # The latitude adjustment is only a transparent development proxy for Philippine exposure.
    latitude_exposure = float(np.clip((abs(latitude) - 5.0) / 15.0, 0, 1))
    typhoon_probability = float(np.clip(0.06 + 0.05 * latitude_exposure, 0.05, 0.12))
    return {
        "temperature_anomaly_c": float(temperature_anomaly),
        "rainfall_ratio": float(rainfall_ratio),
        "drought_probability": float(drought_probability),
        "extreme_rain_probability": float(extreme_rain_probability),
        "heat_probability": float(heat_probability),
        "typhoon_probability": float(typhoon_probability),
    }


def generate_annual_trajectory(request: ClimateTrajectoryRequest) -> dict[str, Any]:
    rng = np.random.default_rng(request.seed)
    years = []
    previous_temp_noise = 0.0
    for year in range(request.start_year, request.end_year + 1):
        params = year_climate_parameters(year, request.scenario, request.latitude)
        normal_probability = max(0.05, 1 - sum(params[k] for k in ["drought_probability", "extreme_rain_probability", "heat_probability", "typhoon_probability"]))
        probabilities = np.array([
            normal_probability,
            params["drought_probability"],
            params["extreme_rain_probability"],
            params["heat_probability"],
            params["typhoon_probability"],
        ])
        probabilities /= probabilities.sum()
        event = str(rng.choice(["normal", "drought", "extreme_rain", "heat_stress", "typhoon"], p=probabilities))
        previous_temp_noise = 0.55 * previous_temp_noise + rng.normal(0, 0.25)
        mean_temp = 27.0 + params["temperature_anomaly_c"] + previous_temp_noise
        rainfall = 2200 * params["rainfall_ratio"] * rng.lognormal(mean=-0.5 * 0.12**2, sigma=0.12)
        event_severity = float(np.clip(rng.beta(2.2, 2.5), 0.05, 0.98))
        if event == "drought":
            rainfall *= 1 - 0.25 - 0.35 * event_severity
        elif event == "extreme_rain":
            rainfall *= 1 + 0.25 + 0.50 * event_severity
        elif event == "heat_stress":
            mean_temp += 0.5 + 1.2 * event_severity
        climate_stress = float(np.clip(
            0.15 + max(0, mean_temp - 28) * 0.09 + abs(rainfall - 2200) / 5000
            + (0.22 * event_severity if event != "normal" else 0), 0, 1
        ))
        years.append({
            "year": year,
            "event": event,
            "event_severity": round(event_severity, 4),
            "annual_rainfall_mm": round(float(rainfall), 1),
            "mean_temperature_c": round(float(mean_temp), 2),
            "climate_stress": round(climate_stress, 4),
            "parameters": {k: round(v, 5) for k, v in params.items()},
        })
    return {
        "scenario": request.scenario,
        "seed": request.seed,
        "start_year": request.start_year,
        "end_year": request.end_year,
        "trajectory": years,
        "label": "Plausible simulated future, not an exact forecast",
        "data_source_type": "synthetic_reference_based",
    }
