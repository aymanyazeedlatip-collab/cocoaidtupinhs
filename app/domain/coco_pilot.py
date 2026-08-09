from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime

CocoPilotMode = Literal[
    "explain_result",
    "compare_scenarios",
    "work_plan",
    "risk_summary",
    "uncertainty",
    "report_narrative",
]
CocoPilotProviderMode = Literal["deterministic", "gemini_if_configured"]
CocoPilotProvider = Literal["deterministic", "google_ai"]
CocoPilotStatus = Literal["completed", "completed_with_fallback", "failed"]
FormalReportFormat = Literal["docx", "pdf"]


class CocoPilotRequest(VersionedContract):
    analysis_run_id: UUID
    mode: CocoPilotMode = "explain_result"
    question: str | None = Field(default=None, max_length=2000)
    provider_mode: CocoPilotProviderMode = "deterministic"
    include_pca_references: bool = True
    generated_at: datetime

    @field_validator("generated_at")
    @classmethod
    def aware_generated_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "generated_at")


class CocoPilotCitation(VersionedContract):
    citation_id: str = Field(min_length=1, max_length=120)
    source_type: str = Field(min_length=1, max_length=80)
    source_id: str = Field(min_length=1, max_length=180)
    title: str = Field(min_length=1, max_length=500)
    source_field: str | None = Field(default=None, max_length=240)
    source_page: str | None = Field(default=None, max_length=80)
    claim: str = Field(min_length=1, max_length=1200)


class CocoPilotRedactionSummary(VersionedContract):
    pii_fields_removed: int = Field(ge=0)
    restricted_sources_excluded: int = Field(ge=0)
    raw_farmer_records_included: bool = False
    farmer_names_included: bool = False


class CocoPilotResponse(TimeStampedContract):
    run_id: UUID = Field(default_factory=uuid4)
    analysis_run_id: UUID
    mode: CocoPilotMode
    provider: CocoPilotProvider
    provider_model: str | None = Field(default=None, max_length=160)
    status: CocoPilotStatus
    conclusion: str = Field(min_length=1, max_length=2400)
    bullets: list[str] = Field(default_factory=list, max_length=8)
    action_line: str = Field(min_length=1, max_length=1200)
    full_text: str = Field(min_length=1, max_length=16000)
    citations: list[CocoPilotCitation] = Field(default_factory=list, max_length=80)
    source_manifest: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    redaction_summary: CocoPilotRedactionSummary
    warnings: list[str] = Field(default_factory=list, max_length=50)
    limitations: list[str] = Field(default_factory=list, max_length=50)


class FormalReportRequest(VersionedContract):
    analysis_run_id: UUID
    report_format: FormalReportFormat = "docx"
    narrative_run_id: UUID | None = None
    title: str | None = Field(default=None, max_length=300)
    generated_at: datetime

    @field_validator("generated_at")
    @classmethod
    def aware_generated_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "generated_at")


class FormalReportRecord(TimeStampedContract):
    report_id: UUID = Field(default_factory=uuid4)
    analysis_run_id: UUID
    narrative_run_id: UUID | None = None
    report_format: FormalReportFormat
    filename: str = Field(min_length=1, max_length=300)
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_version: str = Field(min_length=1, max_length=120)
    source_manifest: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=50)
    data_notice: str = Field(min_length=1, max_length=3000)
