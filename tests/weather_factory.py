from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

RETRIEVED_AT = datetime(2026, 8, 3, 6, 0, tzinfo=UTC)
TIMEZONE = "Asia/Manila"
LATITUDE = 6.334
LONGITUDE = 124.952


def make_open_meteo_payload(*, forecast_rain_adjustment: float = 0.0, stale: bool = False, reference_at: datetime | None = None) -> dict:
    """Build deterministic Open-Meteo-shaped data with history and >16 future days.

    The extra future days intentionally verify that the assimilation boundary trims
    live weather to 16 days rather than trusting an oversized provider payload.
    """
    tz = ZoneInfo(TIMEZONE)
    local_reference = (reference_at or RETRIEVED_AT).astimezone(tz)
    start_day = local_reference.date() - timedelta(days=92)
    end_day = local_reference.date() + timedelta(days=20)
    days = (end_day - start_day).days + 1
    daily_dates = [start_day + timedelta(days=i) for i in range(days)]

    precipitation: list[float] = []
    temperature_max: list[float] = []
    temperature_min: list[float] = []
    temperature_mean: list[float] = []
    wind_speed_max: list[float] = []
    wind_gust_max: list[float] = []
    radiation: list[float] = []
    et0: list[float] = []
    humidity_mean: list[float] = []
    vpd_max: list[float] = []
    weather_codes: list[int] = []
    probability: list[int] = []

    for day_value in daily_dates:
        offset = (day_value - local_reference.date()).days
        base_rain = 0.5 if -2 <= offset <= 0 else 2.0
        if offset >= 0:
            base_rain += forecast_rain_adjustment
        precipitation.append(round(base_rain, 3))
        max_temp = 34.0 if offset % 5 == 0 else 31.0
        temperature_max.append(max_temp)
        temperature_min.append(23.0)
        temperature_mean.append((max_temp + 23.0) / 2)
        wind_speed_max.append(18.0)
        wind_gust_max.append(26.0 + max(0, offset) * 0.1)
        radiation.append(18.0)
        et0.append(1.0)
        humidity_mean.append(75.0)
        vpd_max.append(1.2)
        weather_codes.append(61 if base_rain >= 1 else 3)
        probability.append(70 if base_rain >= 1 else 20)

    hourly_times: list[str] = []
    hourly_values: dict[str, list] = {
        "temperature_2m": [],
        "relative_humidity_2m": [],
        "precipitation_probability": [],
        "precipitation": [],
        "weather_code": [],
        "cloud_cover": [],
        "pressure_msl": [],
        "wind_speed_10m": [],
        "wind_direction_10m": [],
        "wind_gusts_10m": [],
        "vapour_pressure_deficit": [],
        "et0_fao_evapotranspiration": [],
        "soil_moisture_0_to_1cm": [],
        "soil_moisture_1_to_3cm": [],
        "shortwave_radiation": [],
    }
    for day_value in daily_dates:
        offset = (day_value - local_reference.date()).days
        for hour in range(24):
            local_dt = datetime.combine(day_value, time(hour=hour), tzinfo=tz)
            hourly_times.append(local_dt.replace(tzinfo=None).isoformat(timespec="minutes"))
            hourly_values["temperature_2m"].append(29.0)
            hourly_values["relative_humidity_2m"].append(75.0)
            hourly_values["precipitation_probability"].append(50)
            rain = 0.0
            if hour == 16:
                rain = 0.5 if -2 <= offset <= 0 else 2.0
                if offset >= 0:
                    rain += forecast_rain_adjustment
            hourly_values["precipitation"].append(round(rain, 3))
            hourly_values["weather_code"].append(61 if rain else 3)
            hourly_values["cloud_cover"].append(65)
            hourly_values["pressure_msl"].append(1010.0)
            hourly_values["wind_speed_10m"].append(10.0)
            hourly_values["wind_direction_10m"].append(90)
            hourly_values["wind_gusts_10m"].append(20.0)
            hourly_values["vapour_pressure_deficit"].append(0.8)
            hourly_values["et0_fao_evapotranspiration"].append(0.04)
            hourly_values["soil_moisture_0_to_1cm"].append(0.30)
            hourly_values["soil_moisture_1_to_3cm"].append(0.32)
            hourly_values["shortwave_radiation"].append(400.0 if 7 <= hour <= 17 else 0.0)

    payload = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "elevation": 80.0,
        "generationtime_ms": 1.5,
        "utc_offset_seconds": 28800,
        "timezone": TIMEZONE,
        "timezone_abbreviation": "GMT+8",
        "current_units": {
            "time": "iso8601", "interval": "seconds", "temperature_2m": "°C",
            "relative_humidity_2m": "%", "precipitation": "mm", "pressure_msl": "hPa",
            "wind_speed_10m": "km/h", "wind_gusts_10m": "km/h",
            "vapour_pressure_deficit": "kPa", "et0_fao_evapotranspiration": "mm",
            "soil_moisture_0_to_1cm": "m³/m³", "shortwave_radiation": "W/m²",
        },
        "current": {
            "time": local_reference.replace(tzinfo=None).isoformat(timespec="minutes"),
            "interval": 900,
            "temperature_2m": 29.0,
            "relative_humidity_2m": 75.0,
            "precipitation": 0.0,
            "pressure_msl": 1010.0,
            "wind_speed_10m": 10.0,
            "wind_gusts_10m": 20.0,
            "vapour_pressure_deficit": 0.8,
            "et0_fao_evapotranspiration": 0.04,
            "soil_moisture_0_to_1cm": 0.30,
            "shortwave_radiation": 400.0,
        },
        "hourly_units": {
            "time": "iso8601", "temperature_2m": "°C", "relative_humidity_2m": "%",
            "precipitation_probability": "%", "precipitation": "mm", "weather_code": "wmo code",
            "cloud_cover": "%", "pressure_msl": "hPa", "wind_speed_10m": "km/h",
            "wind_direction_10m": "°", "wind_gusts_10m": "km/h",
            "vapour_pressure_deficit": "kPa", "et0_fao_evapotranspiration": "mm",
            "soil_moisture_0_to_1cm": "m³/m³", "soil_moisture_1_to_3cm": "m³/m³",
            "shortwave_radiation": "W/m²",
        },
        "hourly": {"time": hourly_times, **hourly_values},
        "daily_units": {
            "time": "iso8601", "weather_code": "wmo code", "temperature_2m_max": "°C",
            "temperature_2m_min": "°C", "temperature_2m_mean": "°C", "precipitation_sum": "mm",
            "precipitation_probability_max": "%", "wind_speed_10m_max": "km/h",
            "wind_gusts_10m_max": "km/h", "shortwave_radiation_sum": "MJ/m²",
            "et0_fao_evapotranspiration": "mm", "relative_humidity_2m_mean": "%",
            "vapour_pressure_deficit_max": "kPa",
        },
        "daily": {
            "time": [item.isoformat() for item in daily_dates],
            "weather_code": weather_codes,
            "temperature_2m_max": temperature_max,
            "temperature_2m_min": temperature_min,
            "temperature_2m_mean": temperature_mean,
            "precipitation_sum": precipitation,
            "precipitation_probability_max": probability,
            "wind_speed_10m_max": wind_speed_max,
            "wind_gusts_10m_max": wind_gust_max,
            "shortwave_radiation_sum": radiation,
            "et0_fao_evapotranspiration": et0,
            "relative_humidity_2m_mean": humidity_mean,
            "vapour_pressure_deficit_max": vpd_max,
        },
        "metadata": {"is_stale": stale},
    }
    return deepcopy(payload)
