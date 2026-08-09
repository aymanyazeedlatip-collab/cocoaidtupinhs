from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.domain.contract_registry import contract_registry
from app.engines.catalog import DESCRIPTORS
from app.storage.migrations import MIGRATIONS, MigrationManager
from app.weather.assimilation.features import FEATURE_ADAPTER_VERSION

FEATURES = [
    ("rainfall_7d_mm", "mm", 7, "reference_only"),
    ("rainfall_30d_mm", "mm", 30, "reference_only"),
    ("rainfall_90d_mm", "mm", 90, "reference_only"),
    ("moisture_balance_30d_mm", "mm", 30, "reference_only"),
    ("moisture_balance_90d_mm", "mm", 90, "reference_only"),
    ("consecutive_dry_days", "day", 92, "reference_only"),
    ("heat_stress_days_30d", "day", 30, "reference_only"),
    ("forecast_rainfall_16d_mm", "mm", 16, "live_forecast"),
    ("forecast_heat_stress_days_16d", "day", 16, "live_forecast"),
    ("forecast_max_wind_gust_16d_kmh", "km/h", 16, "live_forecast"),
    ("mean_solar_radiation_90d_mj_m2_day", "MJ/m2/day", 90, "reference_only"),
    ("mean_relative_humidity_30d_percent", "percent", 30, "reference_only"),
    ("mean_vpd_30d_kpa", "kPa", 30, "reference_only"),
    ("mean_soil_moisture_30d_fraction", "m3/m3", 30, "reference_only"),
]

ENDPOINTS = [
    {"method": "GET", "path": "/api/v2/weather/status"},
    {"method": "POST", "path": "/api/v2/weather/assimilate"},
    {"method": "GET", "path": "/api/v2/weather/runs"},
    {"method": "GET", "path": "/api/v2/weather/runs/{run_id}"},
    {"method": "GET", "path": "/api/v2/weather/runs/{run_id}/features"},
    {"method": "GET", "path": "/api/v2/weather/compare"},
]


def main() -> int:
    destination = ROOT / "manifests"
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cocoaid-phase3-manifest-") as temp:
        database = Path(temp) / "phase3.sqlite3"
        applied = MigrationManager(database).upgrade()
    weather_contracts = {
        item.name: item.schema_sha256
        for item in contract_registry.catalog()
        if item.name in {"WeatherModelRun", "WeatherFeatureSet", "WeatherAssimilationPayload"}
    }
    payloads = {
        "phase3_migration_catalog.json": {
            "applied_in_clean_database": applied,
            "migrations": [
                {
                    "version": item.version,
                    "name": item.name,
                    "checksum": item.checksum,
                    "destructive_down": item.destructive_down,
                }
                for item in MIGRATIONS
            ],
        },
        "phase3_weather_feature_catalog.json": {
            "feature_adapter_version": FEATURE_ADAPTER_VERSION,
            "live_forecast_limit_days": settings.max_live_forecast_days,
            "features": [
                {"name": name, "unit": unit, "window_days": window, "basis": basis}
                for name, unit, window, basis in FEATURES
            ],
        },
        "phase3_endpoint_catalog.json": {
            "contract_api_version": settings.contract_api_version,
            "endpoints": ENDPOINTS,
        },
        "phase3_contract_hashes.json": weather_contracts,
        "phase3_engine_catalog.json": [
            item.model_dump(mode="json") for item in DESCRIPTORS if item.engine_id == "v3.weather_assimilation"
        ],
    }
    for filename, payload in payloads.items():
        (destination / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
        )
    print("Phase 3 manifests exported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
