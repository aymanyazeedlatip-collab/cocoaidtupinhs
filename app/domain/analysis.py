from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.provenance import RunProvenance


class EngineResultEnvelope(TimeStampedContract):
    engine_id: str = Field(min_length=1, max_length=160)
    engine_version: str = Field(min_length=1, max_length=120)
    status: Literal["succeeded", "failed", "skipped", "degraded"]
    input_contract: str = Field(min_length=1, max_length=160)
    output_contract: str = Field(min_length=1, max_length=160)
    output: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list, max_length=100)
    errors: list[str] = Field(default_factory=list, max_length=100)
    duration_ms: float = Field(ge=0)


class AnalysisRun(TimeStampedContract):
    analysis_run_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["queued", "running", "completed", "partially_completed", "failed"]
    requested_engines: list[str] = Field(min_length=1, max_length=100)
    engine_results: list[EngineResultEnvelope] = Field(default_factory=list, max_length=100)
    provenance: RunProvenance

    @field_validator("started_at", "completed_at")
    @classmethod
    def aware_datetimes(cls, value: datetime | None, info):
        return require_aware_datetime(value, info.field_name) if value is not None else value


class ContractCatalogEntry(VersionedContract):
    name: str
    module: str
    schema_version: str
    schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    description: str
