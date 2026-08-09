from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import ConfidenceLevel
from app.domain.provenance import RunProvenance

DecisionComponent = Literal["production", "bayesian", "pest", "intercropping", "rehabilitation"]
FailurePolicy = Literal["continue_optional", "strict"]
RunStatus = Literal["completed", "partially_completed", "failed"]
ComponentStatus = Literal["succeeded", "failed", "skipped", "degraded"]
RecommendationPriority = Literal["routine", "low", "moderate", "high", "critical"]


class DecisionSupportRequest(VersionedContract):
    farm_id: UUID
    production_forecast_id: UUID
    posterior_id: UUID | None = None
    pest_assessment_run_id: UUID | None = None
    intercropping_run_id: UUID | None = None
    rehabilitation_plan_id: UUID | None = None
    generated_at: datetime
    requested_components: list[DecisionComponent] = Field(
        default_factory=lambda: ["production", "bayesian", "pest", "intercropping", "rehabilitation"],
        min_length=1,
        max_length=5,
    )
    failure_policy: FailurePolicy = "continue_optional"
    farm_data_version: str = Field(min_length=1, max_length=120)

    @field_validator("generated_at")
    @classmethod
    def aware_generated_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "generated_at")

    @model_validator(mode="after")
    def unique_components(self) -> "DecisionSupportRequest":
        if len(self.requested_components) != len(set(self.requested_components)):
            raise ValueError("requested_components must not contain duplicates")
        if "production" not in self.requested_components:
            raise ValueError("production must be included because all decision outputs depend on it")
        return self


class DecisionComponentResult(VersionedContract):
    component: DecisionComponent
    engine_id: str = Field(min_length=1, max_length=160)
    status: ComponentStatus
    record_id: UUID | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    errors: list[str] = Field(default_factory=list, max_length=100)


class DecisionEvidence(VersionedContract):
    source_component: DecisionComponent
    source_engine: str = Field(min_length=1, max_length=160)
    record_id: str = Field(min_length=1, max_length=180)
    field: str = Field(min_length=1, max_length=180)
    value: Any
    explanation: str = Field(min_length=1, max_length=1200)


class DecisionRecommendation(TimeStampedContract):
    recommendation_id: UUID = Field(default_factory=uuid4)
    category: str = Field(min_length=1, max_length=120)
    priority: RecommendationPriority
    title: str = Field(min_length=1, max_length=240)
    action: str = Field(min_length=1, max_length=1600)
    rationale: str = Field(min_length=1, max_length=2000)
    confidence: ConfidenceLevel
    source_components: list[DecisionComponent] = Field(min_length=1, max_length=5)
    evidence: list[DecisionEvidence] = Field(min_length=1, max_length=50)
    requires_field_confirmation: bool = False
    limitations: list[str] = Field(default_factory=list, max_length=30)


class DecisionTraceEdge(VersionedContract):
    upstream_component: DecisionComponent
    downstream_component: DecisionComponent
    relationship: str = Field(min_length=1, max_length=500)
    upstream_record_id: str | None = Field(default=None, max_length=180)
    downstream_record_id: str | None = Field(default=None, max_length=180)


class DecisionOverview(VersionedContract):
    production_estimate: float = Field(ge=0)
    production_unit: str = Field(min_length=1, max_length=80)
    production_lower: float | None = Field(default=None, ge=0)
    production_upper: float | None = Field(default=None, ge=0)
    probability_of_decline: float | None = Field(default=None, ge=0, le=1)
    probability_of_recovery: float | None = Field(default=None, ge=0, le=1)
    highest_pest_id: str | None = Field(default=None, max_length=160)
    highest_pest_probability: float | None = Field(default=None, ge=0, le=1)
    best_intercrop_id: str | None = Field(default=None, max_length=160)
    best_intercrop_score: float | None = Field(default=None, ge=0, le=100)
    selected_rehabilitation_scenario: str | None = Field(default=None, max_length=160)
    selected_rehabilitation_cost_php: float | None = Field(default=None, ge=0)
    urgent_recommendation_count: int = Field(default=0, ge=0)
    data_completeness: float = Field(ge=0, le=1)


class DecisionSupportRecord(TimeStampedContract):
    analysis_run_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    generated_at: datetime
    status: RunStatus
    requested_components: list[DecisionComponent] = Field(min_length=1, max_length=5)
    component_results: list[DecisionComponentResult] = Field(min_length=1, max_length=5)
    overview: DecisionOverview
    recommendations: list[DecisionRecommendation] = Field(default_factory=list, max_length=100)
    traceability: list[DecisionTraceEdge] = Field(default_factory=list, max_length=100)
    provenance: RunProvenance
    warnings: list[str] = Field(default_factory=list, max_length=100)
    data_notice: str = Field(min_length=1, max_length=3000)

    @field_validator("generated_at")
    @classmethod
    def aware_record_time(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "generated_at")


class DecisionSupportSummary(VersionedContract):
    analysis_run_id: UUID
    status: RunStatus
    succeeded_components: int = Field(ge=0)
    skipped_components: int = Field(ge=0)
    failed_components: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)
    urgent_recommendation_count: int = Field(ge=0)
    data_completeness: float = Field(ge=0, le=1)


class DecisionSupportEngineOutput(TimeStampedContract):
    record: DecisionSupportRecord
    summary: DecisionSupportSummary
    parameter_version: str = Field(min_length=1, max_length=120)
    dependency_graph_version: str = Field(min_length=1, max_length=120)
    warnings: list[str] = Field(default_factory=list, max_length=100)
