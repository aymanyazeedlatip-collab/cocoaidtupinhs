from __future__ import annotations

import asyncio
import logging
import math
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from app.core.config import settings
from app.core.errors import ProviderRateLimitError, ProviderUnavailableError
from app.schemas.common import SourceMetadata
from app.schemas.weather import WeatherCubeRequest, WeatherGridRequest, WeatherPointRequest
from app.services.cache import cache
from app.services.persistent_cache import persistent_cache
from app.weather.http import get_json, get_text

logger = logging.getLogger(__name__)

CURRENT_VARIABLES = [
    "temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation",
    "weather_code", "cloud_cover", "pressure_msl", "wind_speed_10m", "wind_direction_10m",
    "wind_gusts_10m", "vapour_pressure_deficit", "et0_fao_evapotranspiration",
    "soil_moisture_0_to_1cm", "shortwave_radiation",
]
HOURLY_VARIABLES = [
    "temperature_2m", "relative_humidity_2m", "precipitation_probability", "precipitation",
    "weather_code", "cloud_cover", "pressure_msl", "wind_speed_10m", "wind_direction_10m",
    "wind_gusts_10m", "vapour_pressure_deficit", "et0_fao_evapotranspiration",
    "soil_moisture_0_to_1cm", "soil_moisture_1_to_3cm", "shortwave_radiation",
]
DAILY_VARIABLES = [
    "weather_code", "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
    "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max",
    "wind_gusts_10m_max", "shortwave_radiation_sum", "et0_fao_evapotranspiration",
]
UNITS = {
    "temperature_2m": "°C", "relative_humidity_2m": "%", "apparent_temperature": "°C",
    "precipitation": "mm", "precipitation_probability": "%", "cloud_cover": "%",
    "pressure_msl": "hPa", "wind_speed_10m": "km/h", "wind_direction_10m": "°",
    "wind_gusts_10m": "km/h", "vapour_pressure_deficit": "kPa",
    "et0_fao_evapotranspiration": "mm", "soil_moisture_0_to_1cm": "m³/m³",
    "soil_moisture_1_to_3cm": "m³/m³", "shortwave_radiation": "W/m²",
}


_provider_cooldown_until = 0.0
_grid_locks: dict[str, asyncio.Lock] = {}
_grid_locks_guard = asyncio.Lock()


def _now() -> datetime:
    return datetime.now(UTC)


def _weather_metadata(valid_time: datetime | None = None, stale: bool = False, model: str = "auto") -> dict:
    return SourceMetadata(
        source=f"Open-Meteo ({model})",
        source_type="Cached deterministic forecast" if stale else "Deterministic forecast",
        retrieved_at=_now(), forecast_valid_at=valid_time, units=UNITS, is_stale=stale,
        limitations=[
            "Forecast fields are numerical weather-model output, not direct observations.",
            "The animated rain-cloud layer visualizes forecast cloud and precipitation fields, not a future satellite photograph.",
            *( ["A recent cached forecast is shown because the live provider was unavailable or rate-limited."] if stale else [] ),
        ],
        attribution="Weather data by Open-Meteo.com and underlying meteorological agencies.",
    ).model_dump(mode="json")


def _cooldown_remaining() -> int:
    return max(0, int(_provider_cooldown_until - time.monotonic()))


def _activate_cooldown() -> None:
    global _provider_cooldown_until
    _provider_cooldown_until = max(_provider_cooldown_until, time.monotonic() + settings.provider_cooldown_seconds)


def _cached_weather_result(value: dict, *, model: str, stale: bool, offline: bool = False) -> dict:
    """Return a disclosed cache response without pretending a provider call occurred now."""
    result = dict(value)
    existing_metadata = dict(value.get("metadata") or {})
    original_retrieved_at = existing_metadata.get("retrieved_at")
    refreshed = _weather_metadata(stale=stale, model=model)
    if original_retrieved_at is not None:
        refreshed["retrieved_at"] = original_retrieved_at
    refreshed["served_at"] = _now().isoformat()
    refreshed["served_from_cache"] = True
    refreshed["live_provider_contacted"] = False
    if offline:
        refreshed["offline_cache"] = True
    result["metadata"] = {**existing_metadata, **refreshed}
    return result


async def fetch_point_forecast(request: WeatherPointRequest, *, force_refresh: bool = False) -> dict:
    key = (
        f"weather-point-v3:{request.latitude:.3f}:{request.longitude:.3f}:{request.model}:"
        f"f{request.forecast_days}:p{request.past_days}"
    )
    cached = None if force_refresh else cache.get(key)
    disk = None if force_refresh or cached is not None else persistent_cache.get(key, settings.cache_ttl_weather_seconds)
    if disk is not None:
        cache.set(key, disk, settings.cache_ttl_weather_seconds)
    stale = cache.get_stale(key, settings.stale_weather_seconds) or persistent_cache.get(
        key, settings.cache_ttl_weather_seconds + settings.stale_weather_seconds
    )
    if settings.offline_mode:
        if cached is not None or disk is not None:
            return _cached_weather_result(cached or disk, model=request.model, stale=False, offline=True)
        if stale is not None:
            return _cached_weather_result(stale, model=request.model, stale=True, offline=True)
        raise ProviderUnavailableError("Live weather is disabled in offline mode and no cached forecast is available")
    if cached is not None:
        return cached
    if disk is not None:
        return disk
    if _cooldown_remaining() > 0:
        if stale is not None:
            return _cached_weather_result(stale, model=request.model, stale=True)
        raise ProviderRateLimitError(f"Weather provider cooling down for about {_cooldown_remaining()} seconds")
    params: dict[str, Any] = {
        "latitude": round(request.latitude, 4), "longitude": round(request.longitude, 4),
        "current": ",".join(CURRENT_VARIABLES), "hourly": ",".join(HOURLY_VARIABLES), "daily": ",".join(DAILY_VARIABLES),
        "timezone": "auto", "forecast_days": request.forecast_days,
        "past_days": request.past_days, "wind_speed_unit": "kmh",
    }
    if request.model != "auto":
        params["models"] = request.model
    try:
        payload = await get_json(settings.open_meteo_base_url, params)
    except ProviderRateLimitError:
        _activate_cooldown()
        if stale is not None:
            return _cached_weather_result(stale, model=request.model, stale=True)
        raise
    except ProviderUnavailableError:
        if stale is not None:
            return _cached_weather_result(stale, model=request.model, stale=True)
        raise
    if not isinstance(payload, dict) or "hourly" not in payload:
        raise ProviderUnavailableError("Open-Meteo response did not include hourly data")
    result = {
        "latitude": float(payload.get("latitude", request.latitude)),
        "longitude": float(payload.get("longitude", request.longitude)),
        "elevation": payload.get("elevation"),
        "generationtime_ms": payload.get("generationtime_ms"),
        "utc_offset_seconds": payload.get("utc_offset_seconds"),
        "timezone": str(payload.get("timezone", "UTC")),
        "timezone_abbreviation": payload.get("timezone_abbreviation"),
        "current_units": payload.get("current_units", {}),
        "current": payload.get("current", {}),
        "hourly_units": payload.get("hourly_units", {}),
        "hourly": payload.get("hourly", {}),
        "daily_units": payload.get("daily_units", {}),
        "daily": payload.get("daily", {}),
        "metadata": _weather_metadata(model=request.model),
    }
    result["metadata"]["forecast_horizon_days"] = request.forecast_days
    result["metadata"]["past_days_requested"] = request.past_days
    cache.set(key, result, settings.cache_ttl_weather_seconds)
    persistent_cache.set(key, result)
    return result


async def point_forecast(request: WeatherPointRequest) -> dict:
    payload = await fetch_point_forecast(request)
    from app.weather.assimilation.service import record_live_point_payload
    return record_live_point_payload(payload, request)


def _snap_bounds(request: WeatherGridRequest) -> tuple[float, float, float, float]:
    step = 0.25
    west = math.floor(request.west / step) * step
    south = math.floor(request.south / step) * step
    east = math.ceil(request.east / step) * step
    north = math.ceil(request.north / step) * step
    return round(west, 2), round(south, 2), round(east, 2), round(north, 2)


def _coordinate_grid(west: float, south: float, east: float, north: float, rows: int, cols: int):
    latitudes = [north - (north - south) * r / (rows - 1) for r in range(rows)]
    longitudes = [west + (east - west) * c / (cols - 1) for c in range(cols)]
    flat_lats, flat_lons = [], []
    for lat in latitudes:
        for lon in longitudes:
            flat_lats.append(round(lat, 4)); flat_lons.append(round(lon, 4))
    return latitudes, longitudes, flat_lats, flat_lons


async def _lock_for(key: str) -> asyncio.Lock:
    async with _grid_locks_guard:
        if key not in _grid_locks and len(_grid_locks) >= 128:
            for old_key, lock in list(_grid_locks.items()):
                if not lock.locked():
                    _grid_locks.pop(old_key, None)
                    if len(_grid_locks) < 96:
                        break
        return _grid_locks.setdefault(key, asyncio.Lock())


async def weather_grid(request: WeatherGridRequest) -> dict:
    if request.rows * request.cols > settings.max_grid_points:
        raise ValueError(f"Grid may contain at most {settings.max_grid_points} points")
    if request.east - request.west > settings.max_bbox_span_degrees or request.north - request.south > settings.max_bbox_span_degrees:
        raise ValueError("Weather grid bounding box exceeds the allowed span")
    west, south, east, north = _snap_bounds(request)
    variable_key = ",".join(sorted(request.variables))
    key = f"weather-grid-v2:{west}:{south}:{east}:{north}:{request.rows}:{request.cols}:{request.model}:{request.forecast_hours}:{variable_key}"
    memory = cache.get(key)
    disk = None if memory is not None else persistent_cache.get(key, settings.cache_ttl_weather_seconds)
    if disk is not None:
        cache.set(key, disk, settings.cache_ttl_weather_seconds)
    stale = cache.get_stale(key, settings.stale_weather_seconds) or persistent_cache.get(
        key, settings.cache_ttl_weather_seconds + settings.stale_weather_seconds
    )
    if settings.offline_mode:
        if memory is not None or disk is not None:
            return _cached_weather_result(memory or disk, model=request.model, stale=False, offline=True)
        if stale is not None:
            return _cached_weather_result(stale, model=request.model, stale=True, offline=True)
        raise ProviderUnavailableError("Live weather is disabled in offline mode and no cached weather grid is available")
    if memory is not None:
        return memory
    if disk is not None:
        return disk
    lock = await _lock_for(key)
    async with lock:
        memory = cache.get(key)
        if memory is not None:
            return memory
        stale = cache.get_stale(key, settings.stale_weather_seconds) or persistent_cache.get(key, settings.cache_ttl_weather_seconds + settings.stale_weather_seconds)
        if _cooldown_remaining() > 0:
            if stale:
                return _cached_weather_result(stale, model=request.model, stale=True)
            raise ProviderRateLimitError(f"Weather provider cooling down for about {_cooldown_remaining()} seconds")
        latitudes, longitudes, flat_lats, flat_lons = _coordinate_grid(west, south, east, north, request.rows, request.cols)
        params: dict[str, Any] = {
            "latitude": ",".join(map(str, flat_lats)), "longitude": ",".join(map(str, flat_lons)),
            "hourly": ",".join(request.variables), "timezone": "UTC", "forecast_hours": request.forecast_hours, "wind_speed_unit": "kmh",
        }
        if request.model != "auto": params["models"] = request.model
        try:
            payload = await get_json(settings.open_meteo_base_url, params)
        except ProviderRateLimitError:
            _activate_cooldown()
            if stale:
                return _cached_weather_result(stale, model=request.model, stale=True)
            raise
        except ProviderUnavailableError:
            if stale:
                return _cached_weather_result(stale, model=request.model, stale=True)
            raise
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != request.rows * request.cols:
            raise ProviderUnavailableError(f"Open-Meteo returned {len(locations)} points; expected {request.rows * request.cols}")
        times = locations[0].get("hourly", {}).get("time", [])
        if not times:
            raise ProviderUnavailableError("Forecast grid contained no valid times")
        values: dict[str, list[list[float | None]]] = {}
        for variable in request.variables:
            values[variable] = []
            for location in locations:
                series = location.get("hourly", {}).get(variable, [])
                values[variable].append([float(v) if v is not None else None for v in series[:len(times)]])
        elevations_flat = []
        for location in locations:
            raw_elevation = location.get("elevation")
            try:
                elevations_flat.append(float(raw_elevation) if raw_elevation is not None else None)
            except (TypeError, ValueError):
                elevations_flat.append(None)
        elevation_grid = [
            elevations_flat[row * request.cols:(row + 1) * request.cols]
            for row in range(request.rows)
        ]
        metadata = _weather_metadata(model=request.model)
        metadata["terrain_note"] = (
            "Wind arrows are adjusted using the elevation values returned for the forecast-grid coordinates. "
            "This is a visualization-scale terrain deflection, not computational fluid dynamics."
        )
        result = {
            "west": west, "south": south, "east": east, "north": north,
            "rows": request.rows, "cols": request.cols, "latitudes": latitudes, "longitudes": longitudes,
            "times": times, "values": values, "elevation_m": elevation_grid, "metadata": metadata,
        }
        cache.set(key, result, settings.cache_ttl_weather_seconds)
        persistent_cache.set(key, result)
        return result


async def weather_cube(request: WeatherCubeRequest) -> dict:
    """Return one reusable multi-variable forecast cube for the TV-style viewer."""
    grid_request = WeatherGridRequest(
        west=request.west, south=request.south, east=request.east, north=request.north,
        rows=request.rows, cols=request.cols,
        variables=[
            "precipitation", "temperature_2m", "cloud_cover", "pressure_msl",
            "wind_speed_10m", "wind_direction_10m", "relative_humidity_2m",
        ],
        forecast_hours=request.forecast_hours, model=request.model,
    )
    return await weather_grid(grid_request)


async def geocode(query: str, count: int = 6) -> dict:
    if settings.offline_mode:
        return {"results": [], "message": "Geocoding unavailable in offline mode"}
    key = f"geocode:{query.strip().lower()}:{count}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    payload = await get_json(settings.open_meteo_geocoding_url, {"name": query, "count": count, "language": "en", "format": "json"})
    results = []
    if isinstance(payload, dict):
        for item in payload.get("results", []):
            if "latitude" in item and "longitude" in item:
                results.append({
                    "name": item.get("name", "Unknown"), "latitude": item["latitude"], "longitude": item["longitude"],
                    "country": item.get("country"), "admin1": item.get("admin1"), "admin2": item.get("admin2"), "timezone": item.get("timezone"),
                })
    result = {"results": results}
    cache.set(key, result, 86400)
    return result


async def radar_frames() -> dict:
    if settings.offline_mode:
        raise ProviderUnavailableError("Radar unavailable in offline mode")
    key = "rainviewer:frames"
    cached = cache.get(key)
    if cached is not None:
        return cached
    payload = await get_json(settings.rainviewer_url)
    if not isinstance(payload, dict) or not payload.get("host"):
        raise ProviderUnavailableError("RainViewer metadata response was invalid")
    frames = []
    radar = payload.get("radar", {})
    for kind in ("past", "nowcast"):
        for item in radar.get(kind, []) or []:
            if "time" in item and "path" in item:
                frames.append({
                    "time": datetime.fromtimestamp(int(item["time"]), UTC).isoformat(),
                    "unix_time": int(item["time"]), "path": str(item["path"]), "kind": kind,
                })
    frames.sort(key=lambda x: x["unix_time"])
    result = {
        "host": payload["host"], "generated_at": datetime.fromtimestamp(int(payload.get("generated", time.time())), UTC).isoformat(),
        "frames": frames, "tile_template": "{host}{path}/256/{z}/{x}/{y}/2/1_1.png",
        "metadata": SourceMetadata(
            source="RainViewer Weather Maps API", source_type="Radar observation", retrieved_at=_now(),
            observed_at=datetime.fromtimestamp(frames[-1]["unix_time"], UTC) if frames else None,
            attribution="Radar data © RainViewer and original radar data providers.",
            limitations=["Radar coverage varies by location.", "Public tiles are limited in zoom and availability."],
        ).model_dump(mode="json"),
    }
    cache.set(key, result, 300)
    return result


def parse_gdacs_rss(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    events = []
    geo_ns = "http://www.georss.org/georss"
    for item in root.findall(".//item"):
        categories = [(e.text or "").strip().upper() for e in item.findall("category")]
        title = (item.findtext("title") or "").strip()
        if "TC" not in categories and "TROPICAL CYCLONE" not in title.upper():
            continue
        point = item.find(f"{{{geo_ns}}}point")
        lat = lon = None
        if point is not None and point.text:
            parts = point.text.split()
            if len(parts) >= 2:
                try: lat, lon = float(parts[0]), float(parts[1])
                except ValueError: pass
        pub = None
        if item.findtext("pubDate"):
            try: pub = parsedate_to_datetime(item.findtext("pubDate")).astimezone(UTC).isoformat()
            except Exception: pass
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", item.findtext("description") or "")).strip()
        events.append({
            "id": (item.findtext("guid") or item.findtext("link") or title).strip(),
            "name": re.sub(r"^.*?TROPICAL CYCLONE\s*", "", title, flags=re.I).strip(" :-") or title,
            "latitude": lat, "longitude": lon, "published_at": pub, "description": desc,
            "source_url": item.findtext("link"), "alert_level": next((c.title() for c in categories if c in {"GREEN", "ORANGE", "RED"}), None),
        })
    return events


async def active_storms() -> dict:
    if settings.offline_mode:
        raise ProviderUnavailableError("Live storm information unavailable in offline mode")
    key = "gdacs:storms"
    cached = cache.get(key)
    if cached is not None:
        return cached
    # GDACS maintains an RSS endpoint; the API URL can vary, so use a stable public feed.
    xml = await get_text("https://www.gdacs.org/xml/rss.xml")
    result = {
        "events": parse_gdacs_rss(xml),
        "official_philippines_reference": "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin",
        "metadata": SourceMetadata(
            source="GDACS", source_type="Supplemental tropical-cyclone information", retrieved_at=_now(),
            attribution="GDACS and contributing meteorological agencies.",
            limitations=["Use PAGASA for official Philippine warnings.", "A public feed may not include complete track geometry."],
        ).model_dump(mode="json"),
    }
    cache.set(key, result, 900)
    return result
