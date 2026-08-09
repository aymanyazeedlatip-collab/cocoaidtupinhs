from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import ConfidenceLevel, DataQualityFlag, SourceType


class SourceReference(VersionedContract):
    source_id: str = Field(min_length=1, max_length=180)
    title: str = Field(min_length=1, max_length=500)
    source_type: SourceType
    organization: str | None = Field(default=None, max_length=240)
    document_version: str | None = Field(default=None, max_length=120)
    page_or_section: str | None = Field(default=None, max_length=120)
    uri_or_path: str | None = Field(default=None, max_length=1000)
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class VersionReference(VersionedContract):
    component: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=120)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class DataProvenance(TimeStampedContract):
    provenance_id: UUID = Field(default_factory=uuid4)
    source: SourceReference
    observed_at: datetime | None = None
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    quality_flags: list[DataQualityFlag] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    transformation_notes: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("observed_at", "retrieved_at", "valid_from", "valid_to")
    @classmethod
    def aware_optional_datetime(cls, value: datetime | None, info):
        return require_aware_datetime(value, info.field_name) if value is not None else value


class RunProvenance(TimeStampedContract):
    run_id: UUID = Field(default_factory=uuid4)
    farm_data_version: str = Field(min_length=1, max_length=120)
    weather_run_id: UUID | None = None
    model_versions: list[VersionReference] = Field(default_factory=list)
    parameter_versions: list[VersionReference] = Field(default_factory=list)
    source_versions: list[VersionReference] = Field(default_factory=list)
    feature_adapter_version: str | None = Field(default=None, max_length=120)
    simulation_seed: int | None = None
    simulation_count: int | None = Field(default=None, ge=1, le=1_000_000)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)
