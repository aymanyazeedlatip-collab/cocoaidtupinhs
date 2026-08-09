from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import DataQualityFlag, WeatherDataKind
from app.domain.provenance import SourceReference
from app.domain.units import UnitCode

MAX_LIVE_FORECAST_DAYS = 16


class WeatherVariable(StrEnum):
    PRECIPITATION = "precipitation"
    TEMPERATURE_MEAN = "temperature_mean"
    TEMPERATURE_MAX = "temperature_max"
    TEMPERATURE_MIN = "temperature_min"
    RELATIVE_HUMIDITY = "relative_humidity"
    VAPOR_PRESSURE_DEFICIT = "vapor_pressure_deficit"
    REFERENCE_EVAPOTRANSPIRATION = "reference_evapotranspiration"
    SOIL_MOISTURE = "soil_moisture"
    SOLAR_RADIATION = "solar_radiation"
    WIND_SPEED = "wind_speed"
    WIND_GUST = "wind_gust"
    CLOUD_COVER = "cloud_cover"
    PRESSURE = "pressure"


class WeatherModelRun(TimeStampedContract):
    weather_run_id: UUID = Field(default_factory=uuid4)
    provider: str = Field(min_length=1, max_length=160)
    provider_model: str = Field(min_length=1, max_length=160)
    data_kind: WeatherDataKind
    model_run_at: datetime | None = None
    retrieved_at: datetime
    valid_from: datetime
    valid_to: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    variables: list[WeatherVariable] = Field(min_length=1)
    source: SourceReference
    units: dict[WeatherVariable, UnitCode] = Field(default_factory=dict)
    raw_payload_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    quality_flags: list[DataQualityFlag] = Field(default_factory=list)
    provider_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("model_run_at", "retrieved_at", "valid_from", "valid_to")
    @classmethod
    def aware_datetimes(cls, value: datetime | None, info):
        if value is None and info.field_name == "model_run_at":
            return None
        return require_aware_datetime(value, info.field_name)

    @model_validator(mode="after")
    def validate_time_window(self) -> "WeatherModelRun":
        if self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be before valid_from")
        if self.data_kind == WeatherDataKind.FORECAST:
            horizon = self.valid_to - self.valid_from
            if horizon > timedelta(days=MAX_LIVE_FORECAST_DAYS):
                raise ValueError(f"Live numerical forecasts may not exceed {MAX_LIVE_FORECAST_DAYS} days")
        missing_units = [variable for variable in self.variables if variable not in self.units]
        if missing_units:
            raise ValueError(f"Missing units for weather variables: {[item.value for item in missing_units]}")
        return self


class WeatherFeature(VersionedContract):
    name: str = Field(min_length=1, max_length=160)
    value: float
    unit: UnitCode
    aggregation_window_days: int | None = Field(default=None, ge=1, le=3660)
    derivation: str = Field(min_length=1, max_length=500)
    quality_flags: list[DataQualityFlag] = Field(default_factory=list)


class WeatherFeatureSet(TimeStampedContract):
    feature_set_id: UUID = Field(default_factory=uuid4)
    weather_run_id: UUID
    farm_id: UUID | None = None
    cell_id: UUID | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    valid_at: datetime
    features: list[WeatherFeature] = Field(min_length=1, max_length=500)
    feature_adapter_version: str = Field(min_length=1, max_length=120)

    @field_validator("valid_at")
    @classmethod
    def aware_valid_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "valid_at")


class WeatherAssimilationPayload(VersionedContract):
    provider_payload: dict[str, Any]
    provider_model: str = Field(default="auto", min_length=1, max_length=160)
    forecast_days: int = Field(default=16, ge=1, le=16)
    history_days: int = Field(default=90, ge=0, le=92)
    farm_id: UUID | None = None
    retrieved_at: datetime | None = None

    @field_validator("retrieved_at")
    @classmethod
    def aware_retrieved_at(cls, value: datetime | None) -> datetime | None:
        return require_aware_datetime(value, "retrieved_at") if value is not None else None
