from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
EnvironmentName = Literal["development", "test", "staging", "production"]
LogFormat = Literal["text", "json"]


class Settings(BaseSettings):
    """Central application configuration.

    Legacy attribute names are intentionally retained so the v2.11 application can
    coexist with the v3 architecture during the controlled migration.
    """

    root_dir: Path = ROOT_DIR
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Product and API identities.
    app_name: str = "COCO-AID"  # Legacy display name retained for compatibility.
    product_name: str = "COCOAID"
    api_version: str = "2.11.0"
    contract_api_version: str = "3.0.0-draft.10"
    legacy_api_prefix: str = "/api"
    v2_api_prefix: str = "/api/v2"
    calculation_version: str = "coco-aid-math-2.4.1"
    parameter_version: str = "psa-calibrated-parameters-2.4.1"

    environment: EnvironmentName = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    offline_mode: bool = False
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"

    # Logging and request observability.
    log_level: str = "INFO"
    log_format: LogFormat = "text"
    request_id_header: str = "X-Request-ID"

    # Feature flags used while legacy and v3 components coexist.
    enable_v2_contract_api: bool = True
    enable_request_metrics: bool = True
    enable_legacy_api: bool = True
    strict_model_runtime_compatibility: bool = False
    auto_seed_reference_data: bool = True
    auto_phase_workflows: bool = False
    auto_phase_poll_seconds: int = Field(default=90, ge=30, le=3600)
    allow_runtime_api_key_configuration: bool = True

    # Persistent paths. PERSISTENT_DATA_DIR can relocate all runtime writes
    # (SQLite, reports, cache, assistant private settings) to a mounted disk.
    persistent_data_dir: Path | None = None
    database_path: Path = ROOT_DIR / "data" / "coco_aid.sqlite3"
    reports_dir: Path = ROOT_DIR / "reports_generated"
    artifacts_dir: Path = ROOT_DIR / "artifacts" / "models"
    model_cards_dir: Path = ROOT_DIR / "artifacts" / "model_cards"
    synthetic_data_path: Path = ROOT_DIR / "data" / "synthetic" / "coconut_farm_years.csv"
    climate_demo_path: Path = ROOT_DIR / "data" / "climate_demo" / "philippines_climate_demo.csv"
    official_production_profiles_path: Path = ROOT_DIR / "data" / "official" / "psa_province_profiles.json"
    cache_dir: Path = ROOT_DIR / "cache"
    private_settings_path: Path = ROOT_DIR / "data" / "private_settings.json"

    # Provider settings.
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    rainviewer_url: str = "https://api.rainviewer.com/public/weather-maps.json"
    gdacs_geojson_url: str = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"
    request_timeout_seconds: float = Field(default=18.0, gt=0, le=120)
    weather_connect_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    weather_read_timeout_seconds: float = Field(default=60.0, gt=0, le=180)
    weather_request_attempts: int = Field(default=2, ge=1, le=5)
    weather_direct_connection_fallback: bool = True
    weather_use_system_trust_store: bool = True
    cache_ttl_weather_seconds: int = Field(default=900, ge=0)
    stale_weather_seconds: int = Field(default=86400, ge=0)
    provider_cooldown_seconds: int = Field(default=300, ge=0)

    # Scientific and operational limits.
    max_grid_points: int = Field(default=49, ge=1, le=400)
    max_bbox_span_degrees: float = Field(default=8.0, gt=0, le=180)
    max_live_forecast_days: int = Field(default=16, ge=1, le=16)
    default_simulation_runs: int = Field(default=1000, ge=100, le=5000)
    max_simulation_runs: int = Field(default=5000, ge=100, le=100000)
    default_start_year: int = Field(default=2026, ge=1900, le=2200)
    default_end_year: int = Field(default=2050, ge=1900, le=2200)

    @field_validator(
        "persistent_data_dir",
        "database_path",
        "reports_dir",
        "artifacts_dir",
        "model_cards_dir",
        "synthetic_data_path",
        "climate_demo_path",
        "official_production_profiles_path",
        "cache_dir",
        "private_settings_path",
        mode="before",
    )
    @classmethod
    def normalize_path(cls, value: Path | str | None) -> Path | None:
        if value is None:
            return None
        path = Path(value).expanduser()
        return path if path.is_absolute() else ROOT_DIR / path


    @model_validator(mode="after")
    def apply_persistent_data_dir(self) -> "Settings":
        """Route runtime-written state to a mounted persistent directory when configured."""
        if self.persistent_data_dir is None:
            return self
        base = Path(self.persistent_data_dir).expanduser()
        if not base.is_absolute():
            base = ROOT_DIR / base
        self.persistent_data_dir = base
        explicitly_set = self.model_fields_set
        if "database_path" not in explicitly_set:
            self.database_path = base / "coco_aid.sqlite3"
        if "reports_dir" not in explicitly_set:
            self.reports_dir = base / "reports"
        if "cache_dir" not in explicitly_set:
            self.cache_dir = base / "cache"
        if "private_settings_path" not in explicitly_set:
            self.private_settings_path = base / "private_settings.json"
        return self

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, value: str) -> str:
        normalized = value.upper().strip()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("log_level must be CRITICAL, ERROR, WARNING, INFO, or DEBUG")
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def public_snapshot(self) -> dict[str, object]:
        """Return non-secret configuration suitable for diagnostics and APIs."""
        return {
            "product_name": self.product_name,
            "legacy_api_version": self.api_version,
            "contract_api_version": self.contract_api_version,
            "environment": self.environment,
            "offline_mode": self.offline_mode,
            "max_live_forecast_days": self.max_live_forecast_days,
            "deployment": {
                "persistent_storage_configured": self.persistent_data_dir is not None,
                "auto_phase_workflows": self.auto_phase_workflows,
                "runtime_api_key_configuration": self.allow_runtime_api_key_configuration,
            },
            "feature_flags": {
                "v2_contract_api": self.enable_v2_contract_api,
                "request_metrics": self.enable_request_metrics,
                "legacy_api": self.enable_legacy_api,
                "strict_model_runtime_compatibility": self.strict_model_runtime_compatibility,
                "auto_seed_reference_data": self.auto_seed_reference_data,
            },
        }


settings = Settings()
