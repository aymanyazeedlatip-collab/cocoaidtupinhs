from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.enums import DataQualityFlag


@dataclass(frozen=True, slots=True)
class NormalizedWeatherValue:
    valid_at: datetime
    period_kind: str
    resolution: str
    variable: str
    value: float | None
    unit: str
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedWeatherRun:
    provider: str
    provider_model: str
    latitude: float
    longitude: float
    timezone: str
    requested_forecast_days: int
    requested_history_days: int
    provider_run_at: datetime | None
    provider_run_time_basis: str
    retrieved_at: datetime
    valid_from: datetime
    valid_to: datetime
    raw_payload_sha256: str
    units: dict[str, str]
    quality_flags: tuple[str, ...]
    provider_metadata: dict[str, Any]
    is_stale: bool
    values: tuple[NormalizedWeatherValue, ...]
    payload_for_storage: dict[str, Any]


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _aware(value: str, timezone: ZoneInfo, *, daily: bool = False) -> datetime:
    if daily:
        parsed_date = date.fromisoformat(value)
        return datetime.combine(parsed_date, time.min, tzinfo=timezone).astimezone(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone)
    return parsed.astimezone(UTC)


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _provider_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove COCOAID-generated metadata before hashing provider content."""
    retained = {
        key: payload.get(key)
        for key in (
            "latitude", "longitude", "elevation", "generationtime_ms", "utc_offset_seconds",
            "timezone", "timezone_abbreviation", "current_units", "current", "hourly_units",
            "hourly", "daily_units", "daily",
        )
        if key in payload
    }
    return retained


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _trim_series(section: dict[str, Any], keep_indices: list[int]) -> dict[str, Any]:
    trimmed: dict[str, Any] = {}
    for key, value in section.items():
        if isinstance(value, list):
            trimmed[key] = [value[index] if index < len(value) else None for index in keep_indices]
        else:
            trimmed[key] = value
    return trimmed


def live_only_payload(payload: dict[str, Any], *, forecast_days: int, retrieved_at: datetime | None = None) -> dict[str, Any]:
    """Return current conditions plus no more than the genuine 16-day live horizon."""
    forecast_days = max(1, min(16, int(forecast_days)))
    result = dict(payload)
    timezone_name = str(payload.get("timezone") or "UTC")
    tz = _timezone(timezone_name)
    reference = (retrieved_at or datetime.now(UTC)).astimezone(tz)
    end_local = datetime.combine(reference.date() + timedelta(days=forecast_days - 1), time.max, tzinfo=tz)

    hourly = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
    hourly_times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    hourly_keep: list[int] = []
    for index, raw_time in enumerate(hourly_times):
        try:
            local = _aware(str(raw_time), tz).astimezone(tz)
        except (ValueError, TypeError):
            continue
        if local >= reference.replace(minute=0, second=0, microsecond=0) and local <= end_local:
            hourly_keep.append(index)
    result["hourly"] = _trim_series(hourly, hourly_keep)

    daily = payload.get("daily") if isinstance(payload.get("daily"), dict) else {}
    daily_times = daily.get("time") if isinstance(daily.get("time"), list) else []
    daily_keep: list[int] = []
    for index, raw_date in enumerate(daily_times):
        try:
            local_date = date.fromisoformat(str(raw_date))
        except ValueError:
            continue
        if reference.date() <= local_date <= reference.date() + timedelta(days=forecast_days - 1):
            daily_keep.append(index)
    result["daily"] = _trim_series(daily, daily_keep)
    result["forecast_horizon_days"] = forecast_days
    result["historical_values_included"] = False
    return result


def normalize_open_meteo_payload(
    payload: dict[str, Any],
    *,
    model: str,
    forecast_days: int,
    history_days: int,
    retrieved_at: datetime | None = None,
) -> NormalizedWeatherRun:
    if not isinstance(payload, dict):
        raise ValueError("Weather provider payload must be an object")
    if not isinstance(payload.get("hourly"), dict) or not payload["hourly"].get("time"):
        raise ValueError("Weather provider payload contains no hourly series")

    retrieved = retrieved_at or datetime.now(UTC)
    if retrieved.tzinfo is None:
        retrieved = retrieved.replace(tzinfo=UTC)
    retrieved = retrieved.astimezone(UTC)
    timezone_name = str(payload.get("timezone") or "UTC")
    tz = _timezone(timezone_name)
    local_reference = retrieved.astimezone(tz)
    forecast_end_date = local_reference.date() + timedelta(days=max(1, min(16, forecast_days)) - 1)
    history_start_date = local_reference.date() - timedelta(days=max(0, min(92, history_days)))

    values: list[NormalizedWeatherValue] = []
    all_units: dict[str, str] = {}

    current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
    current_units = payload.get("current_units") if isinstance(payload.get("current_units"), dict) else {}
    current_time = current.get("time")
    if current_time:
        valid_at = _aware(str(current_time), tz)
        for variable, raw_value in current.items():
            if variable in {"time", "interval"}:
                continue
            unit = str(current_units.get(variable) or "unknown")
            all_units[variable] = unit
            values.append(NormalizedWeatherValue(valid_at, "current", "current", variable, _numeric(raw_value), unit))

    for resolution in ("hourly", "daily"):
        section = payload.get(resolution) if isinstance(payload.get(resolution), dict) else {}
        units = payload.get(f"{resolution}_units") if isinstance(payload.get(f"{resolution}_units"), dict) else {}
        times = section.get("time") if isinstance(section.get("time"), list) else []
        parsed_times: list[datetime] = []
        keep: list[bool] = []
        for raw in times:
            valid_at = _aware(str(raw), tz, daily=resolution == "daily")
            local_date = valid_at.astimezone(tz).date()
            include = history_start_date <= local_date <= forecast_end_date
            parsed_times.append(valid_at)
            keep.append(include)
        for variable, series in section.items():
            if variable == "time" or not isinstance(series, list):
                continue
            unit = str(units.get(variable) or "unknown")
            all_units[variable] = unit
            for index, valid_at in enumerate(parsed_times):
                if not keep[index]:
                    continue
                local_date = valid_at.astimezone(tz).date()
                if local_date < local_reference.date():
                    period_kind = "historical"
                    flags = (DataQualityFlag.REFERENCE_ONLY.value,)
                elif local_date == local_reference.date():
                    period_kind = "current"
                    flags = ()
                else:
                    period_kind = "forecast"
                    flags = ()
                raw_value = series[index] if index < len(series) else None
                values.append(NormalizedWeatherValue(valid_at, period_kind, resolution, variable, _numeric(raw_value), unit, flags))

    live_times = [item.valid_at for item in values if item.period_kind in {"current", "forecast"} and item.resolution in {"hourly", "daily"}]
    if not live_times:
        raise ValueError("Weather provider payload contains no live forecast values")
    valid_from = min(live_times)
    valid_to = max(live_times)
    if valid_to - valid_from > timedelta(days=16):
        valid_to = valid_from + timedelta(days=16)
        values = [item for item in values if item.period_kind == "historical" or item.valid_at <= valid_to]

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    stale = bool(metadata.get("is_stale"))
    quality_flags: list[str] = []
    if stale:
        quality_flags.append(DataQualityFlag.STALE.value)
    if history_days:
        quality_flags.append(DataQualityFlag.REFERENCE_ONLY.value)

    provider_payload = _provider_payload(payload)
    provider_metadata = {
        "generationtime_ms": payload.get("generationtime_ms"),
        "elevation_m": payload.get("elevation"),
        "utc_offset_seconds": payload.get("utc_offset_seconds"),
        "timezone_abbreviation": payload.get("timezone_abbreviation"),
        "provider_run_time_exposed": False,
        "history_basis": "Open-Meteo Forecast API past_days archived forecast values" if history_days else "none",
        "forecast_horizon_policy": "current conditions plus at most 16 forecast days",
    }
    return NormalizedWeatherRun(
        provider="Open-Meteo",
        provider_model=model,
        latitude=float(payload.get("latitude")),
        longitude=float(payload.get("longitude")),
        timezone=timezone_name,
        requested_forecast_days=max(1, min(16, forecast_days)),
        requested_history_days=max(0, min(92, history_days)),
        provider_run_at=None,
        provider_run_time_basis="not_exposed_by_seamless_api",
        retrieved_at=retrieved,
        valid_from=valid_from,
        valid_to=valid_to,
        raw_payload_sha256=_hash_payload(provider_payload),
        units=all_units,
        quality_flags=tuple(dict.fromkeys(quality_flags)),
        provider_metadata=provider_metadata,
        is_stale=stale,
        values=tuple(values),
        payload_for_storage=provider_payload,
    )
