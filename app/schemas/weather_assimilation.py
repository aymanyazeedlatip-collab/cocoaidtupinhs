from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WeatherAssimilationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    model: str = Field(default="auto", min_length=1, max_length=80)
    forecast_days: int = Field(default=16, ge=1, le=16)
    history_days: int = Field(default=90, ge=0, le=92)
    farm_id: UUID | None = None
    force_refresh: bool = False


class WeatherRunListResponse(BaseModel):
    runs: list[dict[str, Any]]
    count: int


class WeatherComparisonRequest(BaseModel):
    base_run_id: UUID
    comparison_run_id: UUID
