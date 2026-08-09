from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import fmean
from typing import Iterable
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.enums import DataQualityFlag
from app.domain.units import UnitCode
from app.domain.weather import WeatherFeature, WeatherFeatureSet
from app.weather.assimilation.normalizer import NormalizedWeatherRun, NormalizedWeatherValue

FEATURE_ADAPTER_VERSION = "weather-features-1.0.0"
DRY_DAY_THRESHOLD_MM = 1.0
HEAT_STRESS_THRESHOLD_C = 33.0


@dataclass(frozen=True, slots=True)
class DailyWeather:
    day: date
    period_kind: str
    values: dict[str, float]


def _run_timezone(run: NormalizedWeatherRun) -> ZoneInfo:
    try:
        return ZoneInfo(run.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _daily_records(run: NormalizedWeatherRun) -> list[DailyWeather]:
    timezone = _run_timezone(run)
    records: dict[date, dict[str, float]] = defaultdict(dict)
    kinds: dict[date, str] = {}
    for item in run.values:
        if item.value is None:
            continue
        day = item.valid_at.astimezone(timezone).date()
        kinds[day] = item.period_kind
        if item.resolution == "daily":
            records[day][item.variable] = item.value
    # Derive daily mean soil moisture from hourly data where no daily provider field exists.
    soil: dict[date, list[float]] = defaultdict(list)
    vpd: dict[date, list[float]] = defaultdict(list)
    humidity: dict[date, list[float]] = defaultdict(list)
    for item in run.values:
        if item.resolution != "hourly" or item.value is None:
            continue
        if item.variable.startswith("soil_moisture_"):
            soil[item.valid_at.astimezone(timezone).date()].append(item.value)
        elif item.variable == "vapour_pressure_deficit":
            vpd[item.valid_at.astimezone(timezone).date()].append(item.value)
        elif item.variable == "relative_humidity_2m":
            humidity[item.valid_at.astimezone(timezone).date()].append(item.value)
    for day, series in soil.items():
        records[day]["soil_moisture_mean"] = fmean(series)
    for day, series in vpd.items():
        records[day]["vapour_pressure_deficit_mean"] = fmean(series)
    for day, series in humidity.items():
        records[day].setdefault("relative_humidity_2m_mean", fmean(series))
    return [DailyWeather(day, kinds.get(day, "historical"), records[day]) for day in sorted(records)]


def _window(records: list[DailyWeather], end_day: date, days: int, *, historical_only: bool = False) -> list[DailyWeather]:
    start = end_day - timedelta(days=days - 1)
    return [
        item for item in records
        if start <= item.day <= end_day and (not historical_only or item.period_kind in {"historical", "current"})
    ]


def _sum(records: Iterable[DailyWeather], variable: str) -> tuple[float, int]:
    values = [item.values[variable] for item in records if variable in item.values]
    return sum(values), len(values)


def _mean(records: Iterable[DailyWeather], variable: str) -> tuple[float, int]:
    values = [item.values[variable] for item in records if variable in item.values]
    return (fmean(values), len(values)) if values else (0.0, 0)


def _flags(actual_days: int, expected_days: int, *, reference_only: bool = False) -> list[DataQualityFlag]:
    flags: list[DataQualityFlag] = []
    if actual_days == 0:
        flags.append(DataQualityFlag.MISSING)
    elif actual_days < expected_days:
        flags.append(DataQualityFlag.LOW_TEMPORAL_RESOLUTION)
    if reference_only:
        flags.append(DataQualityFlag.REFERENCE_ONLY)
    return flags


def build_weather_feature_set(
    run: NormalizedWeatherRun,
    *,
    farm_id: UUID | None = None,
    valid_at: datetime | None = None,
    weather_run_id: UUID | None = None,
) -> WeatherFeatureSet:
    records = _daily_records(run)
    reference_day = (valid_at or run.retrieved_at).astimezone(_run_timezone(run)).date()
    features: list[WeatherFeature] = []

    for days in (7, 30, 90):
        items = _window(records, reference_day, days, historical_only=True)
        value, count = _sum(items, "precipitation_sum")
        features.append(WeatherFeature(
            name=f"rainfall_{days}d_mm", value=value, unit=UnitCode.MILLIMETER,
            aggregation_window_days=days,
            derivation=f"Sum of daily precipitation_sum over the {days}-day window ending {reference_day.isoformat()}.",
            quality_flags=_flags(count, days, reference_only=True),
        ))

    for days in (30, 90):
        items = _window(records, reference_day, days, historical_only=True)
        rain, rain_count = _sum(items, "precipitation_sum")
        et0, et0_count = _sum(items, "et0_fao_evapotranspiration")
        coverage = min(rain_count, et0_count)
        features.append(WeatherFeature(
            name=f"moisture_balance_{days}d_mm", value=rain - et0, unit=UnitCode.MILLIMETER,
            aggregation_window_days=days,
            derivation=f"Daily precipitation sum minus FAO reference evapotranspiration over {days} days.",
            quality_flags=_flags(coverage, days, reference_only=True),
        ))

    historical = _window(records, reference_day, 92, historical_only=True)
    consecutive = 0
    for item in reversed(historical):
        rainfall = item.values.get("precipitation_sum")
        if rainfall is None or rainfall >= DRY_DAY_THRESHOLD_MM:
            break
        consecutive += 1
    features.append(WeatherFeature(
        name="consecutive_dry_days", value=float(consecutive), unit=UnitCode.DAY,
        aggregation_window_days=92,
        derivation=f"Consecutive days ending {reference_day.isoformat()} with precipitation below {DRY_DAY_THRESHOLD_MM} mm/day.",
        quality_flags=[DataQualityFlag.REFERENCE_ONLY],
    ))

    recent30 = _window(records, reference_day, 30, historical_only=True)
    heat_days = sum(1 for item in recent30 if item.values.get("temperature_2m_max", float("-inf")) > HEAT_STRESS_THRESHOLD_C)
    temp_count = sum(1 for item in recent30 if "temperature_2m_max" in item.values)
    features.append(WeatherFeature(
        name="heat_stress_days_30d", value=float(heat_days), unit=UnitCode.DAY,
        aggregation_window_days=30,
        derivation=f"Count of days with maximum 2-m temperature above {HEAT_STRESS_THRESHOLD_C} °C.",
        quality_flags=_flags(temp_count, 30, reference_only=True),
    ))

    forecast = [item for item in records if item.period_kind in {"current", "forecast"} and item.day <= reference_day + timedelta(days=15)]
    forecast_rain, forecast_rain_count = _sum(forecast, "precipitation_sum")
    features.append(WeatherFeature(
        name="forecast_rainfall_16d_mm", value=forecast_rain, unit=UnitCode.MILLIMETER,
        aggregation_window_days=16,
        derivation="Sum of daily precipitation over the current Open-Meteo live numerical forecast horizon only.",
        quality_flags=_flags(forecast_rain_count, 16),
    ))
    forecast_heat = sum(1 for item in forecast if item.values.get("temperature_2m_max", float("-inf")) > HEAT_STRESS_THRESHOLD_C)
    forecast_temp_count = sum(1 for item in forecast if "temperature_2m_max" in item.values)
    features.append(WeatherFeature(
        name="forecast_heat_stress_days_16d", value=float(forecast_heat), unit=UnitCode.DAY,
        aggregation_window_days=16,
        derivation=f"Forecast days with maximum 2-m temperature above {HEAT_STRESS_THRESHOLD_C} °C.",
        quality_flags=_flags(forecast_temp_count, 16),
    ))
    gust_values = [item.values["wind_gusts_10m_max"] for item in forecast if "wind_gusts_10m_max" in item.values]
    features.append(WeatherFeature(
        name="forecast_max_wind_gust_16d_kmh", value=max(gust_values, default=0.0), unit=UnitCode.KILOMETER_PER_HOUR,
        aggregation_window_days=16,
        derivation="Maximum daily 10-m wind gust over the live forecast horizon.",
        quality_flags=_flags(len(gust_values), 16),
    ))

    mean_radiation, radiation_count = _mean(_window(records, reference_day, 90, historical_only=True), "shortwave_radiation_sum")
    features.append(WeatherFeature(
        name="mean_solar_radiation_90d_mj_m2_day", value=mean_radiation,
        unit=UnitCode.MEGAJOULE_PER_SQUARE_METER_DAY, aggregation_window_days=90,
        derivation="Mean daily shortwave radiation sum over 90 days.",
        quality_flags=_flags(radiation_count, 90, reference_only=True),
    ))
    mean_humidity, humidity_count = _mean(recent30, "relative_humidity_2m_mean")
    features.append(WeatherFeature(
        name="mean_relative_humidity_30d_percent", value=mean_humidity, unit=UnitCode.PERCENT,
        aggregation_window_days=30,
        derivation="Mean daily relative humidity over 30 days.",
        quality_flags=_flags(humidity_count, 30, reference_only=True),
    ))
    mean_vpd, vpd_count = _mean(recent30, "vapour_pressure_deficit_mean")
    features.append(WeatherFeature(
        name="mean_vpd_30d_kpa", value=mean_vpd, unit=UnitCode.KILOPASCAL,
        aggregation_window_days=30,
        derivation="Mean hourly vapour-pressure deficit aggregated to daily means over 30 days.",
        quality_flags=_flags(vpd_count, 30, reference_only=True),
    ))
    mean_soil, soil_count = _mean(recent30, "soil_moisture_mean")
    features.append(WeatherFeature(
        name="mean_soil_moisture_30d_fraction", value=mean_soil, unit=UnitCode.CUBIC_METER_PER_CUBIC_METER,
        aggregation_window_days=30,
        derivation="Mean provider-estimated near-surface soil moisture over 30 days.",
        quality_flags=_flags(soil_count, 30, reference_only=True),
    ))

    return WeatherFeatureSet(
        feature_set_id=uuid4(),
        weather_run_id=weather_run_id or UUID(hex=run.raw_payload_sha256[:32]),
        farm_id=farm_id,
        latitude=run.latitude, longitude=run.longitude,
        valid_at=valid_at or run.retrieved_at, features=features,
        feature_adapter_version=FEATURE_ADAPTER_VERSION,
    )
