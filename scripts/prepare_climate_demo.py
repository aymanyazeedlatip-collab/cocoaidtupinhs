from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOCATIONS = [
    ("south_cotabato", 6.334, 124.952, 150),
    ("davao", 7.073, 125.612, 35),
    ("leyte", 11.244, 125.004, 55),
    ("quezon", 13.94, 121.62, 80),
    ("zamboanga", 6.921, 122.079, 25),
    ("bicol", 13.139, 123.743, 60),
]
SCENARIOS = {"ssp126": 0.45, "ssp245": 0.75, "ssp370": 1.05, "ssp585": 1.35}
PERIODS = {"historical": 0.0, "2021-2040": 0.25, "2041-2060": 0.50, "2061-2080": 0.75, "2081-2100": 1.0}
BASE_RAIN = np.array([115, 85, 95, 105, 165, 220, 250, 245, 210, 205, 180, 145], dtype=float)
BASE_TEMP = np.array([26.2, 26.4, 27.0, 27.6, 27.7, 27.2, 26.8, 26.9, 27.0, 27.0, 26.8, 26.4], dtype=float)
BASE_HUM = np.array([77, 75, 74, 74, 77, 81, 82, 82, 82, 82, 81, 79], dtype=float)


def create_climate_demo(path: Path | None = None) -> Path:
    path = path or ROOT / "data" / "climate_demo" / "philippines_climate_demo.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for location_id, lat, lon, elevation in LOCATIONS:
        location_rain_factor = 1 + 0.08 * np.sin(np.radians(lat * 5))
        elevation_temp_adjust = -0.006 * elevation
        for scenario, strength in SCENARIOS.items():
            for period, progress in PERIODS.items():
                for month in range(1, 13):
                    rain = BASE_RAIN[month - 1] * location_rain_factor * (1 - 0.04 * strength * progress + 0.03 * np.sin(month + lat))
                    temp = BASE_TEMP[month - 1] + elevation_temp_adjust + 2.1 * strength * progress
                    humidity = BASE_HUM[month - 1] - 1.8 * strength * progress + 0.02 * rain
                    dry_index = np.clip(0.22 + 0.12 * strength * progress - rain / 1800, 0, 1)
                    heavy_days = max(0, rain / 75 * (1 + 0.08 * strength * progress))
                    heat_days = max(0, (temp - 26.5) * 2.5 + 6 * strength * progress)
                    suitability = np.clip(0.90 - abs(temp - 27) * 0.06 - abs(rain * 12 - 2200) / 10000 - dry_index * 0.20, 0.15, 0.98)
                    rows.append({
                        "location_id": location_id,
                        "latitude": lat,
                        "longitude": lon,
                        "elevation_m": elevation,
                        "scenario": scenario,
                        "period": period,
                        "month": month,
                        "precipitation_mm": round(rain, 3),
                        "mean_temperature_c": round(temp, 3),
                        "minimum_temperature_c": round(temp - 4.2, 3),
                        "maximum_temperature_c": round(temp + 5.0, 3),
                        "relative_humidity_percent": round(np.clip(humidity, 45, 98), 3),
                        "wind_speed_ms": round(2.0 + 0.4 * np.sin(month / 12 * 2 * np.pi) + 0.1 * strength, 3),
                        "consecutive_dry_days_index": round(dry_index, 4),
                        "heavy_rain_days": round(heavy_days, 3),
                        "heat_stress_days": round(heat_days, 3),
                        "drought_tendency": round(dry_index, 4),
                        "coconut_climate_suitability": round(suitability, 4),
                        "temperature_spread_c": round(0.35 + 0.45 * progress, 3),
                        "precipitation_spread_fraction": round(0.08 + 0.12 * progress, 3),
                        "data_source_type": "synthetic_reference_based",
                        "generation_version": "climate-demo-1.0",
                    })
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


if __name__ == "__main__":
    print(create_climate_demo())
