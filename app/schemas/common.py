from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

ProvenanceType = Literal[
    "measured", "farmer_reported", "government_record", "laboratory_test",
    "public_raster", "public_statistic", "estimated", "synthetic_reference_based", "missing",
]


class AnalysisMetadata(BaseModel):
    calculation_version: str
    model_versions: dict[str, str] = Field(default_factory=dict)
    parameter_version: str
    data_source_type: str
    random_seed: int | None = None
    simulation_count: int | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_period: str | None = None
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class SourceMetadata(BaseModel):
    source: str
    source_type: str
    retrieved_at: datetime
    observed_at: datetime | None = None
    forecast_valid_at: datetime | None = None
    model_run_at: datetime | None = None
    units: dict[str, str] = Field(default_factory=dict)
    is_stale: bool = False
    limitations: list[str] = Field(default_factory=list)
    attribution: str


class ApiMessage(BaseModel):
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
