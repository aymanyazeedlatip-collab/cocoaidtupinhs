from __future__ import annotations

import calendar
import math
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any

import numpy as np

from app.climate.projections import climate_projection
from app.core.config import settings
from app.data.official_production import production_calibration
from app.gis.analysis import centroid
from app.math.state import STATES
from app.schemas.analysis import ClimateProjectionRequest, FarmSiteForecastRequest, SimulationRequest
from app.simulation.engine import run_simulation


MONTH_PERIOD = {
    range(2021, 2041): "2021-2040",
    range(2041, 2061): "2041-2060",
}


def _period_for_year(year: int) -> str:
    if year <= 2040:
        return "2021-2040"
    return "2041-2060"


def farm_map_bounds(farm) -> dict[str, float]:
    polygon = farm.location.polygon
    lat = farm.location.latitude
    lon = farm.location.longitude
    if polygon:
        lats = [float(point[0]) for point in polygon]
        lons = [float(point[1]) for point in polygon]
        center = centroid(polygon, (lat, lon))
        lat = float(center["latitude"])
        lon = float(center["longitude"])
        raw_width = max(lons) - min(lons)
        raw_height = max(lats) - min(lats)
    else:
        raw_width = raw_height = 0.0
    # A regional view makes moving systems legible while keeping the farm visible.
    half_width = max(0.75, min(1.75, raw_width * 8 + 0.75))
    half_height = max(0.65, min(1.50, raw_height * 8 + 0.65))
    return {
        "west": round(max(-179.0, lon - half_width), 5),
        "east": round(min(179.0, lon + half_width), 5),
        "south": round(max(-84.0, lat - half_height), 5),
        "north": round(min(84.0, lat + half_height), 5),
        "center_latitude": round(lat, 6),
        "center_longitude": round(lon, 6),
    }


def _condition_score(states: dict[str, float]) -> float:
    total = max(1.0, sum(float(states.get(name, 0.0)) for name in STATES))
    healthy = (float(states.get("productive", 0.0)) + 0.65 * float(states.get("recovering", 0.0))) / total
    burden = (
        0.55 * float(states.get("aging", 0.0))
        + 0.75 * float(states.get("stressed", 0.0))
        + 1.0 * float(states.get("infested", 0.0))
        + 1.0 * float(states.get("dead", 0.0))
    ) / total
    return float(np.clip(0.18 + 0.98 * healthy - 0.55 * burden, 0.0, 1.0))


def _condition_class(score: float) -> str:
    if score >= 0.78:
        return "Good"
    if score >= 0.58:
        return "Watch"
    if score >= 0.38:
        return "Stressed"
    return "Critical"


def _climate_months(latitude: float, longitude: float, scenario: str, period: str) -> dict[int, dict[str, float]]:
    projection = climate_projection(ClimateProjectionRequest(
        latitude=latitude,
        longitude=longitude,
        scenario=scenario,
        period=period,
        model_mode="multi_model_median",
    ))
    return {int(item["month"]): item for item in projection["monthly"]}



def _mean(values: list[float]) -> float:
    finite = [float(value) for value in values if value is not None and np.isfinite(float(value))]
    return float(np.mean(finite)) if finite else 0.0


def _rounded_product_partition(total: float, mature: float, digits: int) -> tuple[float, float, float]:
    """Round a total and its mature/young partition without display-level drift.

    Independently rounding all three values can make Mature + Young differ from
    Coconut (w/ husk) by one final decimal place. The UI and exported reports use
    these values together, so derive the young value from the rounded total.
    """
    rounded_total = round(max(0.0, float(total)), digits)
    rounded_mature = round(float(np.clip(mature, 0.0, max(0.0, float(total)))), digits)
    rounded_mature = min(rounded_total, rounded_mature)
    rounded_young = round(max(0.0, rounded_total - rounded_mature), digits)
    return rounded_total, rounded_mature, rounded_young


def _circular_mean_degrees(values: list[float]) -> float:
    finite = [math.radians(float(value)) for value in values if value is not None and np.isfinite(float(value))]
    if not finite:
        return 0.0
    return float((math.degrees(math.atan2(np.mean(np.sin(finite)), np.mean(np.cos(finite)))) + 360) % 360)


def _aggregate_live_cube(cube: dict[str, Any] | None, farm) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    """Aggregate a real hourly provider cube into local daily farm/map frames.

    The cube is used only within its provider horizon. Later dates continue with the
    climate-conditioned stochastic generator. No synthetic data are relabeled as live.
    """
    if not cube or not cube.get("times") or not cube.get("values"):
        return {}, None
    try:
        rows, cols = int(cube["rows"]), int(cube["cols"])
        latitudes = [float(v) for v in cube["latitudes"]]
        longitudes = [float(v) for v in cube["longitudes"]]
        local_zone = ZoneInfo("Asia/Manila")
        parsed_times: list[datetime] = []
        for value in cube["times"]:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            parsed_times.append(parsed.astimezone(local_zone))
    except (KeyError, TypeError, ValueError):
        return {}, None

    latitude = float(farm.location.latitude)
    longitude = float(farm.location.longitude)
    row = min(range(rows), key=lambda idx: abs(latitudes[idx] - latitude))
    col = min(range(cols), key=lambda idx: abs(longitudes[idx] - longitude))
    farm_point = row * cols + col
    by_date: dict[str, list[int]] = defaultdict(list)
    for index, timestamp in enumerate(parsed_times):
        by_date[timestamp.date().isoformat()].append(index)

    values = cube.get("values", {})
    def point_series(variable: str, point: int) -> list[Any]:
        series = values.get(variable, [])
        return series[point] if point < len(series) else []

    output: dict[str, dict[str, Any]] = {}
    for day_key, indexes in sorted(by_date.items()):
        if not indexes:
            continue
        intensity_grid: list[list[float]] = []
        for r in range(rows):
            grid_row: list[float] = []
            for c in range(cols):
                series = point_series("precipitation", r * cols + c)
                candidates = [float(series[i]) for i in indexes if i < len(series) and series[i] is not None]
                grid_row.append(round(max(candidates, default=0.0), 3))
            intensity_grid.append(grid_row)

        precipitation = point_series("precipitation", farm_point)
        temperatures = point_series("temperature_2m", farm_point)
        clouds = point_series("cloud_cover", farm_point)
        pressures = point_series("pressure_msl", farm_point)
        wind_speeds = point_series("wind_speed_10m", farm_point)
        wind_directions = point_series("wind_direction_10m", farm_point)
        humidities = point_series("relative_humidity_2m", farm_point)
        rain_values = [float(precipitation[i]) for i in indexes if i < len(precipitation) and precipitation[i] is not None]
        temp_values = [float(temperatures[i]) for i in indexes if i < len(temperatures) and temperatures[i] is not None]
        cloud_values = [float(clouds[i]) for i in indexes if i < len(clouds) and clouds[i] is not None]
        pressure_values = [float(pressures[i]) for i in indexes if i < len(pressures) and pressures[i] is not None]
        speed_values = [float(wind_speeds[i]) for i in indexes if i < len(wind_speeds) and wind_speeds[i] is not None]
        direction_values = [float(wind_directions[i]) for i in indexes if i < len(wind_directions) and wind_directions[i] is not None]
        humidity_values = [float(humidities[i]) for i in indexes if i < len(humidities) and humidities[i] is not None]
        peak = max(rain_values, default=0.0)
        output[day_key] = {
            "rainfall_mm": round(sum(rain_values), 2),
            "rain_intensity_mm_h": round(peak, 2),
            "temperature_c": round(_mean(temp_values), 2),
            "temperature_max_c": round(max(temp_values), 2) if temp_values else round(_mean(temp_values), 2),
            "cloud_cover_percent": round(_mean(cloud_values), 1),
            "pressure_hpa": round(_mean(pressure_values), 1),
            "wind_speed_kmh": round(_mean(speed_values), 1),
            "wind_direction_deg": round(_circular_mean_degrees(direction_values), 1),
            "humidity_percent": round(_mean(humidity_values), 1) if humidity_values else None,
            "event": "heavy_rain_forecast" if peak >= 4 else ("rain_forecast" if peak >= 0.1 else "short_term_forecast"),
            "event_severity": round(float(np.clip(peak / 12.0, 0, 1)), 3),
            "data_mode": "deterministic_short_term_forecast",
            "spatial_grid": intensity_grid,
            "grid_bounds": {
                "west": float(cube["west"]), "south": float(cube["south"]),
                "east": float(cube["east"]), "north": float(cube["north"]),
                "rows": rows, "cols": cols,
            },
        }

    metadata = dict(cube.get("metadata") or {})
    metadata.update({
        "first_local_date": min(output) if output else None,
        "last_local_date": max(output) if output else None,
        "timezone": "Asia/Manila",
        "aggregation": "Daily farm values and daily maximum hourly precipitation field from the provider cube",
    })
    return output, metadata

def _event_window(event: str, year: int, severity: float, rng: np.random.Generator) -> tuple[date, date] | None:
    if event == "normal":
        return None
    if event == "typhoon":
        start_month, duration = int(rng.integers(6, 12)), int(4 + round(4 * severity))
    elif event == "drought":
        start_month, duration = int(rng.integers(1, 6)), int(35 + round(55 * severity))
    elif event == "extreme_rain":
        start_month, duration = int(rng.integers(5, 12)), int(7 + round(10 * severity))
    else:  # heat_stress
        start_month, duration = int(rng.integers(2, 7)), int(12 + round(28 * severity))
    max_day = calendar.monthrange(year, start_month)[1]
    start = date(year, start_month, int(rng.integers(1, max(2, max_day - 4))))
    return start, min(date(year, 12, 31), start + timedelta(days=duration - 1))


def _daily_year_weather(
    *,
    year: int,
    scenario: str,
    annual_sample: dict[str, Any],
    climate_months: dict[int, dict[str, float]],
    rng: np.random.Generator,
    center_x: float,
    center_y: float,
    farm_x: float,
    farm_y: float,
) -> tuple[list[dict[str, Any]], float, float]:
    days_in_year = 366 if calendar.isleap(year) else 365
    dates = [date(year, 1, 1) + timedelta(days=i) for i in range(days_in_year)]
    annual_target = max(1.0, float(annual_sample["rainfall_mm"]))
    event = str(annual_sample["event"])
    severity = float(annual_sample["severity"])
    event_window = _event_window(event, year, severity, rng)

    month_targets = np.array([float(climate_months[m]["precipitation_mm"]) for m in range(1, 13)], dtype=float)
    month_targets *= annual_target / max(1e-9, month_targets.sum())

    rainfall = np.zeros(days_in_year, dtype=float)
    temperature = np.zeros(days_in_year, dtype=float)
    humidity = np.zeros(days_in_year, dtype=float)
    wind = np.zeros(days_in_year, dtype=float)
    wind_dir = np.zeros(days_in_year, dtype=float)
    pressure = np.zeros(days_in_year, dtype=float)
    cloud = np.zeros(days_in_year, dtype=float)

    previous_wet = False
    temp_noise = 0.0
    for idx, current_date in enumerate(dates):
        m = current_date.month
        month = climate_months[m]
        target = month_targets[m - 1]
        n_days = calendar.monthrange(year, m)[1]
        expected_wet_days = float(np.clip(target / 11.0, 4, n_days * 0.82))
        base_wet = expected_wet_days / n_days
        p_wet = min(0.92, base_wet * (1.42 if previous_wet else 0.68))
        is_event_day = bool(event_window and event_window[0] <= current_date <= event_window[1])
        if event == "drought" and is_event_day:
            p_wet *= 0.12
        elif event in {"extreme_rain", "typhoon"} and is_event_day:
            p_wet = max(p_wet, 0.88)
        wet = rng.random() < p_wet
        previous_wet = wet
        if wet:
            shape = 1.45 if event != "extreme_rain" else 1.15
            scale = max(1.2, target / max(1.0, expected_wet_days * shape))
            rainfall[idx] = rng.gamma(shape, scale)
        if is_event_day and event == "extreme_rain":
            rainfall[idx] += rng.gamma(2.1, 9.0 + 13.0 * severity)
        elif is_event_day and event == "typhoon":
            phase = (current_date - event_window[0]).days / max(1, (event_window[1] - event_window[0]).days)
            core = math.exp(-((phase - 0.52) / 0.25) ** 2)
            rainfall[idx] += core * (35 + 105 * severity) + rng.gamma(1.5, 4.0)

        temp_noise = 0.72 * temp_noise + rng.normal(0, 0.65)
        temperature[idx] = float(month["mean_temperature_c"]) + temp_noise
        if is_event_day and event in {"drought", "heat_stress"}:
            temperature[idx] += (0.7 if event == "drought" else 1.5) + 1.4 * severity

        humidity[idx] = np.clip(float(month["relative_humidity_percent"]) + 0.18 * rainfall[idx] - 0.65 * max(0, temperature[idx] - 29) + rng.normal(0, 2.4), 40, 100)
        cloud[idx] = np.clip(10 + 0.72 * humidity[idx] + 2.8 * math.sqrt(max(0, rainfall[idx])) + rng.normal(0, 7), 0, 100)
        wind[idx] = max(0.5, float(month["wind_speed_ms"]) * 3.6 + rng.lognormal(0.0, 0.25))
        wind_dir[idx] = (35 + 85 * math.sin(2 * math.pi * idx / days_in_year) + rng.normal(0, 24)) % 360
        pressure[idx] = 1012.5 - 0.07 * rainfall[idx] - 0.045 * wind[idx] + rng.normal(0, 1.8)
        if is_event_day and event == "typhoon":
            phase = (current_date - event_window[0]).days / max(1, (event_window[1] - event_window[0]).days)
            core = math.exp(-((phase - 0.52) / 0.23) ** 2)
            wind[idx] += core * (38 + 92 * severity)
            pressure[idx] -= core * (12 + 28 * severity)
            wind_dir[idx] = (210 + 140 * phase + rng.normal(0, 8)) % 360

    # Match the sampled annual total while retaining the generated daily pattern.
    total_rain = rainfall.sum()
    if total_rain > 0:
        rainfall *= annual_target / total_rain

    result: list[dict[str, Any]] = []
    for idx, current_date in enumerate(dates):
        direction_rad = math.radians(float(wind_dir[idx]))
        movement = min(0.035, 0.0025 + float(wind[idx]) / 2600)
        center_x = (center_x + math.sin(direction_rad) * movement + rng.normal(0, 0.008)) % 1.0
        center_y = (center_y - math.cos(direction_rad) * movement + rng.normal(0, 0.008)) % 1.0
        peak = float(np.clip(rainfall[idx] / max(1.2, 7.0 - 3.0 * severity), 0, 30))
        spread = float(np.clip(0.08 + 0.004 * math.sqrt(max(0, rainfall[idx])) + rng.uniform(0.015, 0.08), 0.07, 0.30))
        if peak >= 0.05:
            # On a farm-rain day the moving regional system must intersect the farm.
            # This keeps the displayed map and farm weather metrics internally consistent.
            attraction = float(np.clip(0.38 + peak / 18.0, 0.38, 0.88))
            center_x = (1 - attraction) * center_x + attraction * farm_x
            center_y = (1 - attraction) * center_y + attraction * farm_y
        seed = int(rng.integers(1, 2_147_000_000))
        is_event_day = bool(event_window and event_window[0] <= current_date <= event_window[1])
        result.append({
            "date": current_date.isoformat(),
            "rainfall_mm": round(float(rainfall[idx]), 2),
            "rain_intensity_mm_h": round(peak, 2),
            "temperature_c": round(float(temperature[idx]), 2),
            "temperature_max_c": round(float(max(
                temperature[idx] + 3.6,
                (33.2 + 3.8 * severity) if (is_event_day and event == "heat_stress") else temperature[idx] + 3.6,
                (31.5 + 2.2 * severity) if (is_event_day and event == "drought") else temperature[idx] + 3.6,
            )), 2),
            "humidity_percent": round(float(humidity[idx]), 1),
            "cloud_cover_percent": round(float(cloud[idx]), 1),
            "pressure_hpa": round(float(pressure[idx]), 1),
            "wind_speed_kmh": round(float(wind[idx]), 1),
            "wind_direction_deg": round(float(wind_dir[idx]), 1),
            "event": event if is_event_day else "normal",
            "event_severity": round(severity if is_event_day else 0.0, 3),
            # Normalized map position and spread drive the TV-style visual layer.
            "spatial": [round(center_x, 4), round(center_y, 4), round(spread, 4), round(peak, 3), seed],
        })
    return result, center_x, center_y



def _quarter_key(month: int) -> str:
    return f"q{min(4, max(1, (month - 1) // 3 + 1))}"


def _category_shares_for_date(calibration: dict[str, Any], current_date: date) -> tuple[float, float]:
    quarter = _quarter_key(current_date.month)
    base_mature = float(calibration.get("mature_share", .97))
    base_young = float(calibration.get("young_share", .03))
    quarter_shares = calibration.get("quarter_shares", {})
    husk_q = float(quarter_shares.get("coconut_w_husk", {}).get(quarter, .25))
    mature_q = float(quarter_shares.get("coconut_mature", {}).get(quarter, .25))
    young_q = float(quarter_shares.get("coconut_young", {}).get(quarter, .25))
    mature_weight = max(0.0, base_mature * mature_q)
    young_weight = max(0.0, base_young * young_q)
    denominator = mature_weight + young_weight
    if denominator <= 0 or husk_q <= 0:
        return base_mature, base_young
    return mature_weight / denominator, young_weight / denominator


def _circular_mean_pairs(values: list[float]) -> float:
    return _circular_mean_degrees(values)


def _weather_adjusted_category_shares(
    calibration: dict[str, Any],
    current_date: date,
    week: dict[str, float],
    antecedent_rainfall_mm: float,
) -> tuple[float, float, dict[str, float]]:
    """Allocate total husked production into mature and young products.

    The official provincial product shares provide the seasonal baseline. Distinct
    physiological response terms then modify the categories before re-normalizing,
    so Mature + Young always equals Coconut (w/ husk) while the composition changes
    with moisture, heat, wind, pest pressure, and farm condition.
    """
    base_mature, base_young = _category_shares_for_date(calibration, current_date)
    rain = max(0.0, float(week.get("rainfall_mm", 0.0)))
    temp = float(week.get("temperature_c", 27.0))
    max_temp = float(week.get("temperature_max_c", temp))
    humidity = float(week.get("humidity_percent", 78.0))
    wind = float(week.get("wind_speed_kmh", 10.0))
    pest = float(np.clip(week.get("pest_probability", 0.15), 0.0, 1.0))
    condition = float(np.clip(week.get("farm_condition_score", 0.65), 0.0, 1.0))
    severity = float(np.clip(week.get("event_severity", 0.0), 0.0, 1.0))
    event = str(week.get("event") or "normal")

    # Four-week moisture availability is more meaningful for fruit development than
    # one isolated wet day. The optimum is broad to avoid false precision.
    water_adequacy = math.exp(-((antecedent_rainfall_mm - 150.0) / 125.0) ** 2)
    drought_stress = float(np.clip((75.0 - antecedent_rainfall_mm) / 75.0, 0.0, 1.0))
    excess_rain_stress = float(np.clip((rain - 190.0) / 240.0, 0.0, 1.0))
    heat_stress = float(np.clip((max_temp - 32.0) / 7.0, 0.0, 1.0))
    warm_support = math.exp(-((temp - 27.5) / 5.2) ** 2)
    humidity_support = math.exp(-((humidity - 80.0) / 18.0) ** 2)
    wind_stress = float(np.clip((wind - 38.0) / 95.0, 0.0, 1.0))

    mature_factor = math.exp(
        0.08 * water_adequacy
        + 0.06 * warm_support
        + 0.05 * condition
        - 0.20 * drought_stress
        - 0.16 * heat_stress
        - 0.20 * wind_stress
        - 0.11 * excess_rain_stress
        - 0.12 * pest
    )
    young_factor = math.exp(
        0.24 * water_adequacy
        + 0.13 * humidity_support
        + 0.08 * condition
        - 0.36 * drought_stress
        - 0.28 * heat_stress
        - 0.30 * wind_stress
        - 0.18 * excess_rain_stress
        - 0.22 * pest
    )

    # Event-specific effects differ because tender-nut output is generally more
    # sensitive to immediate water and wind stress, while mature harvest has a more
    # buffered response.
    if event == "typhoon":
        mature_factor *= max(0.45, 1.0 - 0.28 * severity)
        young_factor *= max(0.25, 1.0 - 0.52 * severity)
    elif event == "drought":
        mature_factor *= max(0.55, 1.0 - 0.24 * severity)
        young_factor *= max(0.35, 1.0 - 0.44 * severity)
    elif event in {"extreme_rain", "heavy_rain_forecast"}:
        mature_factor *= max(0.70, 1.0 - 0.14 * severity)
        young_factor *= max(0.52, 1.0 - 0.30 * severity)
    elif event == "heat_stress":
        mature_factor *= max(0.65, 1.0 - 0.18 * severity)
        young_factor *= max(0.42, 1.0 - 0.38 * severity)

    mature_weight = max(1e-9, base_mature * mature_factor)
    young_weight = max(1e-9, base_young * young_factor)
    total_weight = mature_weight + young_weight
    mature_share = mature_weight / total_weight
    young_share = young_weight / total_weight
    return mature_share, young_share, {
        "base_mature_share": round(base_mature, 6),
        "base_young_share": round(base_young, 6),
        "mature_weather_factor": round(mature_factor, 5),
        "young_weather_factor": round(young_factor, 5),
        "water_adequacy": round(water_adequacy, 5),
        "drought_stress": round(drought_stress, 5),
        "heat_stress": round(heat_stress, 5),
        "wind_stress": round(wind_stress, 5),
        "excess_rain_stress": round(excess_rain_stress, 5),
    }


def _aggregate_weekly_frames(daily_frames: list[dict[str, Any]], calibration: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame in daily_frames:
        current = date.fromisoformat(frame["date"])
        monday = current - timedelta(days=current.weekday())
        groups[monday.isoformat()].append(frame)

    weekly: list[dict[str, Any]] = []
    cumulative_husk = cumulative_mature = cumulative_young = 0.0
    recent_rainfall: list[float] = []
    for week_start, days in sorted(groups.items()):
        days.sort(key=lambda item: item["date"])
        start = date.fromisoformat(days[0]["date"])
        end = date.fromisoformat(days[-1]["date"])
        husk_tons = sum(float(item.get("production_equivalent_kg", 0.0)) for item in days) / 1000.0
        peak_day = max(days, key=lambda item: float(item.get("rain_intensity_mm_h", 0.0)))
        severe_day = max(days, key=lambda item: float(item.get("event_severity", 0.0)))
        deterministic_days = [item for item in days if item.get("data_mode") == "deterministic_short_term_forecast"]
        event = severe_day.get("event", "normal")
        rain_total = sum(float(item.get("rainfall_mm", 0.0)) for item in days)
        max_temp = max(float(item.get("temperature_max_c", item.get("temperature_c", 0.0))) for item in days)
        if event == "normal":
            if max_temp >= 34:
                event = "heat_stress"
            elif rain_total >= 180:
                event = "extreme_rain"
        # Keep event labels physically consistent with the generated weather.
        # A modeled extreme-rain week must actually be wet, and heat stress must
        # actually cross a biologically meaningful daytime maximum threshold.
        if event == "extreme_rain" and rain_total < 70:
            event = "normal"
        if event == "heat_stress" and max_temp < 33:
            event = "normal"

        core = {
            "rainfall_mm": rain_total,
            "temperature_c": _mean([item.get("temperature_c") for item in days]),
            "temperature_max_c": max_temp,
            "humidity_percent": _mean([item.get("humidity_percent") for item in days]),
            "cloud_cover_percent": _mean([item.get("cloud_cover_percent") for item in days]),
            "pressure_hpa": _mean([item.get("pressure_hpa") for item in days]),
            "wind_speed_kmh": _mean([item.get("wind_speed_kmh") for item in days]),
            "wind_direction_deg": _circular_mean_pairs([item.get("wind_direction_deg") for item in days]),
            "event": event,
            "event_severity": max(float(item.get("event_severity", 0.0)) for item in days),
            "farm_condition_score": _mean([item.get("farm_condition_score") for item in days]),
            "pest_probability": _mean([item.get("pest_probability") for item in days]),
        }
        antecedent = sum((recent_rainfall + [rain_total])[-4:])
        mature_share, young_share, product_factors = _weather_adjusted_category_shares(
            calibration, start + (end - start) // 2, core, antecedent
        )
        mature_tons = husk_tons * mature_share
        young_tons = husk_tons * young_share
        # Store the weekly weather-adjusted partition on each daily equivalent so
        # annual totals respect calendar-year boundaries even when a week crosses
        # New Year.
        for item in days:
            daily_husk = float(item.get("production_equivalent_kg", 0.0)) / 1000.0
            item["production_coconut_mature_tons"] = daily_husk * mature_share
            item["production_coconut_young_tons"] = daily_husk * young_share
            item["product_response_factors"] = product_factors
        recent_rainfall.append(rain_total)
        if len(recent_rainfall) > 8:
            recent_rainfall.pop(0)

        cumulative_husk += husk_tons
        cumulative_mature += mature_tons
        cumulative_young += young_tons
        rounded_husk, rounded_mature, rounded_young = _rounded_product_partition(husk_tons, mature_tons, 5)
        rounded_cumulative_husk, rounded_cumulative_mature, rounded_cumulative_young = _rounded_product_partition(
            cumulative_husk, cumulative_mature, 4
        )
        weekly.append({
            "date": start.isoformat(),
            "week_start": start.isoformat(),
            "week_end": end.isoformat(),
            "label": f"{start.strftime('%b %d')}-{end.strftime('%b %d, %Y')}",
            "data_mode": "deterministic_short_term_forecast" if deterministic_days else "plausible_stochastic_climate_simulation",
            "rainfall_mm": round(core["rainfall_mm"], 2),
            "rain_intensity_mm_h": round(max(float(item.get("rain_intensity_mm_h", 0.0)) for item in days), 2),
            "temperature_c": round(core["temperature_c"], 2),
            "temperature_max_c": round(core["temperature_max_c"], 2),
            "humidity_percent": round(core["humidity_percent"], 1),
            "cloud_cover_percent": round(core["cloud_cover_percent"], 1),
            "pressure_hpa": round(core["pressure_hpa"], 1),
            "wind_speed_kmh": round(core["wind_speed_kmh"], 1),
            "wind_direction_deg": round(core["wind_direction_deg"], 1),
            "event": event,
            "event_severity": round(core["event_severity"], 3),
            "spatial": peak_day.get("spatial"),
            "spatial_grid": peak_day.get("spatial_grid"),
            "grid_bounds": peak_day.get("grid_bounds"),
            "production_coconut_w_husk_tons": rounded_husk,
            "production_coconut_mature_tons": rounded_mature,
            "production_coconut_young_tons": rounded_young,
            "mature_share": round(mature_share, 6),
            "young_share": round(young_share, 6),
            "product_response_factors": product_factors,
            "cumulative_coconut_w_husk_tons": rounded_cumulative_husk,
            "cumulative_coconut_mature_tons": rounded_cumulative_mature,
            "cumulative_coconut_young_tons": rounded_cumulative_young,
            "farm_condition_score": round(core["farm_condition_score"], 4),
            "condition_class": days[-1].get("condition_class"),
            "farm_state_estimate": days[-1].get("farm_state_estimate"),
            "pest_probability": round(core["pest_probability"], 4),
            "annual_production_tons": days[-1].get("annual_production_tons"),
        })
    return weekly



def _compact_daily_frames(daily_frames: list[dict[str, Any]], weekly_frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a payload-efficient daily visual timeline linked to weekly model control points.

    The agricultural state engine remains annual and weekly summaries remain the
    reporting control points. Daily frames expose the already generated daily
    weather path and the weather-adjusted daily product allocation so the client
    can animate one calendar date at a time without inventing new API requests.
    """
    week_by_date: dict[str, int] = {}
    for index, week in enumerate(weekly_frames):
        start = date.fromisoformat(week["week_start"])
        end = date.fromisoformat(week["week_end"])
        current = start
        while current <= end:
            week_by_date[current.isoformat()] = index
            current += timedelta(days=1)
    output: list[dict[str, Any]] = []
    keep = (
        "date", "rainfall_mm", "rain_intensity_mm_h", "temperature_c",
        "humidity_percent", "cloud_cover_percent", "pressure_hpa",
        "wind_speed_kmh", "wind_direction_deg", "event", "event_severity",
        "data_mode", "spatial", "spatial_grid", "grid_bounds",
        "farm_condition_score", "condition_class", "pest_probability",
        "production_equivalent_kg", "production_coconut_mature_tons",
        "production_coconut_young_tons", "annual_production_tons",
        "cumulative_production_from_start_tons", "product_response_factors",
    )
    for frame in daily_frames:
        item = {key: frame.get(key) for key in keep if key in frame}
        item["week_index"] = week_by_date.get(str(frame.get("date")), 0)
        item["frame_method"] = "daily weather frame between weekly agricultural control points"
        output.append(item)
    return output

def _annual_product_totals_from_daily(
    daily_frames: list[dict[str, Any]],
    yearly_summary: dict[int, dict[str, Any]],
    annual_states: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    totals: dict[int, dict[str, float]] = defaultdict(lambda: {
        "coconut_w_husk_tons": 0.0,
        "coconut_mature_tons": 0.0,
        "coconut_young_tons": 0.0,
    })
    for frame in daily_frames:
        year = date.fromisoformat(frame["date"]).year
        husk = float(frame.get("production_equivalent_kg", 0.0)) / 1000.0
        mature = float(frame.get("production_coconut_mature_tons", 0.0))
        young = float(frame.get("production_coconut_young_tons", max(0.0, husk - mature)))
        totals[year]["coconut_w_husk_tons"] += husk
        totals[year]["coconut_mature_tons"] += mature
        totals[year]["coconut_young_tons"] += young

    state_by_year = {int(item["year"]): item for item in annual_states}
    output: list[dict[str, Any]] = []
    for year in sorted(totals):
        values = totals[year]
        husk = values["coconut_w_husk_tons"]
        category_total = values["coconut_mature_tons"] + values["coconut_young_tons"]
        if category_total > 0:
            scale = husk / category_total
            values["coconut_mature_tons"] *= scale
            values["coconut_young_tons"] *= scale
        full_year = max(1e-9, float(state_by_year.get(year, {}).get("annual_production_tons", husk)))
        coverage_ratio = float(np.clip(husk / full_year, 0.0, 1.0))
        posterior = yearly_summary[year]
        rounded_husk, rounded_mature, rounded_young = _rounded_product_partition(
            husk, values["coconut_mature_tons"], 3
        )
        output.append({
            "year": year,
            "coconut_w_husk_tons": rounded_husk,
            "coconut_mature_tons": rounded_mature,
            "coconut_young_tons": rounded_young,
            "mature_share": round(rounded_mature / rounded_husk, 6) if rounded_husk else 0.0,
            "young_share": round(rounded_young / rounded_husk, 6) if rounded_husk else 0.0,
            "coverage_ratio": round(coverage_ratio, 5),
            "coverage_label": "partial year from selected start date" if coverage_ratio < 0.985 else "full year",
            "p05": round(float(posterior.get("p05", 0.0)) * coverage_ratio, 4),
            "median": round(float(posterior.get("median", 0.0)) * coverage_ratio, 4),
            "p95": round(float(posterior.get("p95", 0.0)) * coverage_ratio, 4),
        })
    return output


def _build_extreme_events(weekly: list[dict[str, Any]], baseline_annual_tons: float, total_trees: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    normal_week = max(1e-6, baseline_annual_tons / 52.1775)
    event_labels = {
        "typhoon": "Typhoon exposure",
        "drought": "Extended drought",
        "extreme_rain": "Extreme rainfall",
        "heat_stress": "Heat stress",
        "heavy_rain_forecast": "Heavy rain forecast",
        "rain_forecast": "Rain forecast",
    }
    base_damage = {
        "typhoon": 0.46,
        "drought": 0.28,
        "extreme_rain": 0.20,
        "heat_stress": 0.16,
        "heavy_rain_forecast": 0.10,
        "rain_forecast": 0.035,
    }
    affected_factor = {
        "typhoon": 0.45,
        "drought": 0.24,
        "extreme_rain": 0.18,
        "heat_stress": 0.15,
        "heavy_rain_forecast": 0.10,
        "rain_forecast": 0.04,
    }

    def finalize(item: dict[str, Any]) -> dict[str, Any]:
        weeks = max(1, int(item["weeks"]))
        peak = float(np.clip(item["peak_severity"], 0.0, 1.0))
        mean_severity = float(item["severity_sum"]) / weeks
        duration_factor = min(1.55, 0.82 + 0.18 * math.sqrt(weeks))
        severity_factor = 0.12 + 1.28 * (0.65 * peak + 0.35 * mean_severity) ** 1.35
        loss_fraction = float(np.clip(base_damage[item["event_type"]] * severity_factor * duration_factor, 0.0, 0.9))
        severity_loss = normal_week * weeks * loss_fraction
        # Preserve a small contribution from the production path, but severity remains
        # the dominant and monotonic driver of the reported loss estimate.
        modeled_deficit = max(0.0, float(item["modeled_deficit_tons"]))
        estimated_loss = 0.8 * severity_loss + 0.2 * modeled_deficit
        tree_fraction = float(np.clip(affected_factor[item["event_type"]] * (0.20 + 1.15 * peak) * duration_factor, 0.0, 0.95))
        samples = max(1, int(item.get("weather_samples", weeks)))
        item.update({
            "peak_severity": round(peak, 3),
            "mean_severity": round(mean_severity, 3),
            "severity_percent": round(peak * 100.0, 1),
            "estimated_production_loss_tons": round(estimated_loss, 3),
            "loss_percent_of_event_baseline": round(loss_fraction * 100.0, 1),
            "estimated_trees_affected": int(round(total_trees * tree_fraction)),
            "impact_index": round(float(np.clip(100 * (0.62 * peak + 0.38 * loss_fraction), 0, 100)), 1),
            "event_rainfall_total_mm": round(float(item.get("rainfall_total_mm", 0.0)), 1),
            "event_peak_week_rainfall_mm": round(float(item.get("peak_rainfall_mm", 0.0)), 1),
            "event_peak_temperature_c": round(float(item.get("peak_temperature_c", 0.0)), 1),
            "event_peak_wind_kmh": round(float(item.get("peak_wind_kmh", 0.0)), 1),
            "event_peak_wind_direction_deg": round(float(item.get("peak_wind_direction_deg", 0.0)), 0),
            "event_mean_humidity_percent": round(float(item.get("humidity_sum", 0.0)) / samples, 1),
        })
        item["impact_summary"] = (
            f"Peak severity {item['severity_percent']:.1f}/100; estimated loss "
            f"{item['estimated_production_loss_tons']:.2f} t "
            f"({item['loss_percent_of_event_baseline']:.1f}% of the event-period baseline) "
            f"across {weeks} week(s). Approximately {item['estimated_trees_affected']} trees may require inspection."
        )
        item.pop("severity_sum", None)
        item.pop("modeled_deficit_tons", None)
        item.pop("rainfall_total_mm", None)
        item.pop("peak_rainfall_mm", None)
        item.pop("peak_temperature_c", None)
        item.pop("peak_wind_kmh", None)
        item.pop("peak_wind_direction_deg", None)
        item.pop("humidity_sum", None)
        item.pop("weather_samples", None)
        return item

    for frame in weekly:
        kind = str(frame.get("event") or "normal")
        if kind not in event_labels:
            kind = "normal"
        if kind == "normal":
            if active:
                events.append(finalize(active))
                active = None
            continue
        severity = float(np.clip(frame.get("event_severity", 0.0), 0.0, 1.0))
        deficit = max(0.0, normal_week - float(frame.get("production_coconut_w_husk_tons", 0.0)))
        if active and active["event_type"] == kind:
            active["end_date"] = frame["week_end"]
            active["peak_severity"] = max(active["peak_severity"], severity)
            active["severity_sum"] += severity
            active["weeks"] += 1
            active["modeled_deficit_tons"] += deficit
            active["rainfall_total_mm"] += max(0.0, float(frame.get("rainfall_mm", 0.0)))
            active["peak_rainfall_mm"] = max(active["peak_rainfall_mm"], max(0.0, float(frame.get("rainfall_mm", 0.0))))
            active["peak_temperature_c"] = max(active["peak_temperature_c"], float(frame.get("temperature_max_c", frame.get("temperature_c", 0.0))))
            current_wind = max(0.0, float(frame.get("wind_speed_kmh", 0.0)))
            if current_wind >= active["peak_wind_kmh"]:
                active["peak_wind_kmh"] = current_wind
                active["peak_wind_direction_deg"] = float(frame.get("wind_direction_deg", 0.0))
            active["humidity_sum"] += max(0.0, float(frame.get("humidity_percent", 0.0)))
            active["weather_samples"] += 1
        else:
            if active:
                events.append(finalize(active))
            active = {
                "event_type": kind,
                "label": event_labels[kind],
                "start_date": frame["week_start"],
                "end_date": frame["week_end"],
                "peak_severity": severity,
                "severity_sum": severity,
                "weeks": 1,
                "modeled_deficit_tons": deficit,
                "rainfall_total_mm": max(0.0, float(frame.get("rainfall_mm", 0.0))),
                "peak_rainfall_mm": max(0.0, float(frame.get("rainfall_mm", 0.0))),
                "peak_temperature_c": float(frame.get("temperature_max_c", frame.get("temperature_c", 0.0))),
                "peak_wind_kmh": max(0.0, float(frame.get("wind_speed_kmh", 0.0))),
                "peak_wind_direction_deg": float(frame.get("wind_direction_deg", 0.0)),
                "humidity_sum": max(0.0, float(frame.get("humidity_percent", 0.0))),
                "weather_samples": 1,
                "confidence": "Higher near-term confidence" if frame.get("data_mode") == "deterministic_short_term_forecast" else "Scenario-dependent estimate",
                "data_mode": frame.get("data_mode"),
            }
    if active:
        events.append(finalize(active))
    return events

def generate_farm_site_forecast(
    request: FarmSiteForecastRequest,
    live_cube: dict[str, Any] | None = None,
    live_warning: str | None = None,
) -> dict[str, Any]:
    calibration = production_calibration(request.farm.location.province, request.farm.location.region)
    simulation = run_simulation(SimulationRequest(
        farm=request.farm,
        start_year=request.start_year,
        end_year=request.end_year,
        scenario=request.scenario,
        intervention=request.intervention,
        runs=request.runs,
        seed=request.seed,
        recovery_threshold_ratio=request.recovery_threshold_ratio,
        severe_loss_threshold_ratio=request.severe_loss_threshold_ratio,
    ))
    yearly_summary = {int(row["year"]): row for row in simulation["yearly"]}
    sample_by_year = {int(row["year"]): row for row in simulation["sample_trajectory"]}
    live_by_date, live_metadata = _aggregate_live_cube(live_cube, request.farm)
    today = date.today()
    effective_start_date = request.start_date or (
        today if request.start_year == today.year else date(request.start_year, 1, 1)
    )
    if effective_start_date < date(request.start_year, 1, 1):
        effective_start_date = date(request.start_year, 1, 1)
    if effective_start_date > date(request.end_year, 12, 31):
        raise ValueError("The effective start date is outside the requested forecast horizon")
    live_dates_used = sorted(
        key for key in live_by_date
        if effective_start_date <= date.fromisoformat(key) <= date(request.end_year, 12, 31)
    )
    bounds = farm_map_bounds(request.farm)
    farm_map_x = float(np.clip(
        (request.farm.location.longitude - bounds["west"]) / max(1e-9, bounds["east"] - bounds["west"]), 0, 1
    ))
    farm_map_y = float(np.clip(
        (bounds["north"] - request.farm.location.latitude) / max(1e-9, bounds["north"] - bounds["south"]), 0, 1
    ))
    climate_cache: dict[str, dict[int, dict[str, float]]] = {}
    for period in { _period_for_year(y) for y in range(request.start_year, request.end_year + 1) }:
        climate_cache[period] = _climate_months(
            request.farm.location.latitude,
            request.farm.location.longitude,
            request.scenario,
            period,
        )

    rng = np.random.default_rng(np.random.SeedSequence([request.seed, 88317]))
    center_x, center_y = float(rng.uniform(0.15, 0.85)), float(rng.uniform(0.15, 0.85))
    frames: list[dict[str, Any]] = []
    monthly_acc: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "rainfall_mm": 0.0, "temperature_sum": 0.0, "days": 0,
        "production_tons": 0.0, "condition_sum": 0.0,
    })

    previous_states = {
        "young": request.farm.trees.young,
        "productive": request.farm.trees.productive,
        "aging": request.farm.trees.aging,
        "stressed": request.farm.trees.stressed,
        "infested": request.farm.trees.infested,
        "recovering": request.farm.trees.recovering,
        "dead": request.farm.trees.dead,
    }

    annual_states: list[dict[str, Any]] = []
    cumulative_from_start_tons = 0.0
    for year in range(request.start_year, request.end_year + 1):
        annual = sample_by_year[year]
        target_states = annual.get("states") or yearly_summary[year]["mean_states"]
        daily, center_x, center_y = _daily_year_weather(
            year=year,
            scenario=request.scenario,
            annual_sample=annual,
            climate_months=climate_cache[_period_for_year(year)],
            rng=rng,
            center_x=center_x,
            center_y=center_y,
            farm_x=farm_map_x,
            farm_y=farm_map_y,
        )
        # Replace only matching near-term dates with real provider model output.
        # The remainder of the horizon retains the explicitly labelled stochastic path.
        for frame in daily:
            frame["simulation_event"] = frame["event"]
            frame["data_mode"] = "plausible_stochastic_climate_simulation"
            live = live_by_date.get(frame["date"])
            if live:
                generated_humidity = frame.get("humidity_percent")
                frame.update({key: value for key, value in live.items() if value is not None})
                if frame.get("humidity_percent") is None:
                    frame["humidity_percent"] = generated_humidity

        n_days = len(daily)
        annual_production = float(annual["production_tons"])
        raw_weights = np.empty(n_days, dtype=float)
        for i, frame in enumerate(daily):
            temp_stress = abs(float(frame["temperature_c"]) - 27.2) / 16
            moisture_stress = min(1.0, max(0.0, (1.2 - float(frame["rainfall_mm"])) / 8))
            event_penalty = 0.22 * float(frame["event_severity"])
            seasonality = 1.0 + 0.10 * math.sin(2 * math.pi * (i - 42) / n_days)
            raw_weights[i] = max(0.08, seasonality * math.exp(-0.22 * temp_stress - 0.12 * moisture_stress - event_penalty))
        weights = raw_weights / raw_weights.sum()

        start_score = _condition_score(previous_states)
        end_score = _condition_score(target_states)
        year_to_date_equivalent_tons = 0.0
        for i, frame in enumerate(daily):
            fraction = (i + 1) / n_days
            structural_score = start_score + (end_score - start_score) * fraction
            state_estimate = {
                name: max(0.0, float(previous_states.get(name, 0.0)) + (float(target_states.get(name, 0.0)) - float(previous_states.get(name, 0.0))) * fraction)
                for name in STATES
            }
            weather_impulse = (
                0.075 * float(frame["event_severity"])
                + 0.008 * max(0.0, float(frame["temperature_c"]) - 31.0)
                + 0.025 * min(1.0, float(frame["rainfall_mm"]) / 120.0)
            )
            # The transient indicator reacts to the selected day's weather but returns
            # to the annual state trajectory at year boundaries.
            score = float(np.clip(structural_score - weather_impulse * math.sin(math.pi * fraction), 0, 1))
            production_kg = annual_production * 1000 * float(weights[i])
            year_to_date_equivalent_tons += production_kg / 1000
            pest = float(np.clip(
                float(annual["pest_probability"]) + 0.0017 * (float(frame["humidity_percent"]) - 78)
                + 0.002 * math.sqrt(max(0, float(frame["rainfall_mm"])))
                - 0.0012 * max(0, float(frame["temperature_c"]) - 31),
                0.002,
                0.98,
            ))
            frame.update({
                "production_equivalent_kg": round(production_kg, 3),
                "annual_production_tons": round(annual_production, 3),
                "farm_condition_score": round(score, 4),
                "condition_class": _condition_class(score),
                "farm_state_estimate": {name: round(value, 2) for name, value in state_estimate.items()},
                "farm_state_label": "Within-year interpolation between annual stochastic state transitions",
                "pest_probability": round(pest, 4),
                "year_to_date_production_equivalent_tons": round(year_to_date_equivalent_tons, 4),
            })
            if date.fromisoformat(frame["date"]) < effective_start_date:
                continue
            cumulative_from_start_tons += production_kg / 1000
            frame["cumulative_production_from_start_tons"] = round(cumulative_from_start_tons, 4)
            frames.append(frame)
            month_key = frame["date"][:7]
            acc = monthly_acc[month_key]
            acc["rainfall_mm"] += float(frame["rainfall_mm"])
            acc["temperature_sum"] += float(frame["temperature_c"])
            acc["days"] += 1
            acc["production_tons"] += production_kg / 1000
            acc["condition_sum"] += score

        annual_states.append({
            "year": year,
            "states": {name: round(float(target_states[name]), 2) for name in STATES},
            "condition_score": round(end_score, 4),
            "condition_class": _condition_class(end_score),
            "annual_production_tons": round(annual_production, 3),
            "event": annual["event"],
            "event_severity": annual["severity"],
            "pest_probability": annual["pest_probability"],
        })
        previous_states = target_states

    monthly = []
    for month, acc in sorted(monthly_acc.items()):
        monthly.append({
            "month": month,
            "rainfall_mm": round(acc["rainfall_mm"], 1),
            "mean_temperature_c": round(acc["temperature_sum"] / max(1, acc["days"]), 2),
            "production_tons": round(acc["production_tons"], 4),
            "condition_score": round(acc["condition_sum"] / max(1, acc["days"]), 4),
        })

    weekly = _aggregate_weekly_frames(frames, calibration)
    daily_visual_frames = _compact_daily_frames(frames, weekly)
    extreme_events = _build_extreme_events(
        weekly,
        baseline_annual_tons=float(request.farm.production.annual_production_tons),
        total_trees=int(request.farm.trees.total_trees),
    )
    annual_by_product = _annual_product_totals_from_daily(
        frames, yearly_summary, annual_states
    )

    return {
        "farm": {
            "name": request.farm.name,
            "latitude": request.farm.location.latitude,
            "longitude": request.farm.location.longitude,
            "polygon": request.farm.location.polygon,
            "area_hectares": request.farm.area_hectares,
        },
        "map_bounds": bounds,
        "farm_map_position": {"x": round(farm_map_x, 5), "y": round(farm_map_y, 5)},
        "scenario": request.scenario,
        "intervention": request.intervention,
        "start_year": request.start_year,
        "end_year": request.end_year,
        "effective_start_date": effective_start_date.isoformat(),
        "effective_end_date": date(request.end_year, 12, 31).isoformat(),
        "short_term_live_merge": {
            "requested": request.include_live_short_term,
            "available": bool(live_dates_used),
            "dates_merged": len(live_dates_used),
            "first_merged_date": live_dates_used[0] if live_dates_used else None,
            "last_merged_date": live_dates_used[-1] if live_dates_used else None,
            "metadata": live_metadata,
            "warning": live_warning,
        },
        "seed": request.seed,
        "runs": request.runs,
        "frames": weekly,
        "weekly": weekly,
        "daily_frames": daily_visual_frames,
        "daily_frame_count": len(daily_visual_frames),
        "timeline_resolution": "daily_visual_frames_with_weekly_agricultural_control_points",
        "playback_scale": "1 second equals 2 daily frames (two days)",
        "monthly": monthly,
        "annual_states": annual_states,
        "annual_by_product": annual_by_product,
        "extreme_events": extreme_events,
        "official_production_reference": calibration,
        "posterior_summary": simulation["summary"],
        "posterior_yearly": simulation["yearly"],
        "data_source_type": "mixed_official_psa_calibration_and_model_projection",
        "label": "Hybrid farm outlook: short-term provider forecast when available, followed by a plausible climate-conditioned projection",
        "production_label": "Weekly production equivalents are partitioned into Coconut Mature and Coconut Young categories using official provincial seasonality plus distinct weather-response equations.",
        "product_model": {
            "identity": "Coconut with husk = Coconut Mature + Coconut Young",
            "mature_response": "Base mature share × exp(water support + temperature support + condition - drought - heat - wind - excess rain - pest pressure)",
            "young_response": "Base young share × exp(stronger water and humidity support - stronger drought, heat, wind, excess-rain and pest penalties)",
            "normalization": "The two weather-adjusted category weights are normalized every week to conserve total husked production.",
        },
        "data_mode_explanation": {
            "deterministic_short_term_forecast": "Real numerical weather-model output aggregated to local calendar days; still a forecast, not an observation.",
            "plausible_stochastic_climate_simulation": "Climate-conditioned generated weather path used after the numerical forecast horizon; not an exact prediction.",
        },
        "calculation_version": settings.calculation_version,
        "parameter_version": settings.parameter_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "warnings": [
            *([live_warning] if live_warning else []),
            "Only dates tagged deterministic_short_term_forecast use current provider model output; later dates are simulated possibilities.",
            "Long-term colored weather fields are model-generated visualizations, not future radar or satellite images.",
            "Daily and weekly production equivalents are allocations of annual simulated production, not a guaranteed harvest for an exact date.",
            "PSA provincial production observations calibrate the three product series; unavailable periods are explicitly tagged as estimates in provenance.",
        ],
        "limitations": simulation["limitations"],
    }
