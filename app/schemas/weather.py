from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.common import SourceMetadata

SUPPORTED_GRID_VARIABLES = {
    "precipitation", "temperature_2m", "cloud_cover", "pressure_msl",
    "wind_speed_10m", "wind_direction_10m", "relative_humidity_2m"
}


class WeatherPointRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    model: str = Field(default="auto", max_length=80)
    forecast_days: int = Field(default=16, ge=1, le=16)
    past_days: int = Field(default=0, ge=0, le=92)


class WeatherGridRequest(BaseModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    rows: int = Field(default=6, ge=3, le=10)
    cols: int = Field(default=6, ge=3, le=10)
    variables: list[str] = Field(default_factory=lambda: list(SUPPORTED_GRID_VARIABLES))
    forecast_hours: int = Field(default=72, ge=12, le=384)
    model: str = Field(default="auto", max_length=80)

    @field_validator("variables")
    @classmethod
    def variables_supported(cls, values: list[str]) -> list[str]:
        values = list(dict.fromkeys(values))
        invalid = [v for v in values if v not in SUPPORTED_GRID_VARIABLES]
        if invalid:
            raise ValueError(f"Unsupported variables: {invalid}")
        return values

    @model_validator(mode="after")
    def bbox_valid(self) -> "WeatherGridRequest":
        if self.east <= self.west or self.north <= self.south:
            raise ValueError("Invalid bounding box")
        return self


class WeatherFrameRequest(BaseModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    rows: int = Field(default=6, ge=3, le=10)
    cols: int = Field(default=6, ge=3, le=10)
    variables: list[str] = Field(default_factory=lambda: ["precipitation"])
    hour_index: int = Field(default=0, ge=0, le=383)
    model: str = Field(default="auto", max_length=80)

    @field_validator("variables")
    @classmethod
    def variables_supported(cls, values: list[str]) -> list[str]:
        values = list(dict.fromkeys(values))
        invalid = [v for v in values if v not in SUPPORTED_GRID_VARIABLES]
        if invalid:
            raise ValueError(f"Unsupported variables: {invalid}")
        if not values:
            raise ValueError("At least one variable is required")
        return values

    @model_validator(mode="after")
    def bbox_valid(self) -> "WeatherFrameRequest":
        if self.east <= self.west or self.north <= self.south:
            raise ValueError("Invalid bounding box")
        return self


class WeatherCubeRequest(BaseModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    rows: int = Field(default=6, ge=3, le=10)
    cols: int = Field(default=6, ge=3, le=10)
    model: str = Field(default="auto", max_length=80)
    forecast_hours: int = Field(default=384, ge=12, le=384)

    @model_validator(mode="after")
    def bbox_valid(self) -> "WeatherCubeRequest":
        if self.east <= self.west or self.north <= self.south:
            raise ValueError("Invalid bounding box")
        return self


class PointForecastResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str
    current: dict[str, Any]
    hourly: dict[str, list[Any]]
    daily: dict[str, list[Any]]
    metadata: SourceMetadata


class RadarFrame(BaseModel):
    time: datetime
    unix_time: int
    path: str
    kind: Literal["past", "nowcast"] = "past"
