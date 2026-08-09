from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import StrictModel, TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import ConfidenceLevel, EvidenceStatus
from app.domain.provenance import RunProvenance, SourceReference
from app.domain.units import UnitCode

PestRiskClass = Literal["low", "moderate", "high", "critical"]
PestDirection = Literal["increases_risk", "decreases_risk", "diagnostic_signal"]
PestContributionSource = Literal[
    "pca_rule", "weather_feature", "farm_context", "symptom", "field_observation",
    "spatial_case", "management_protection", "baseline_prior",
]


class PestEvidence(VersionedContract):
    """Compatibility contract retained from Phase 1."""

    evidence_id: UUID = Field(default_factory=uuid4)
    pest_profile_id: str = Field(min_length=1, max_length=160)
    status: EvidenceStatus
    observed_at: datetime | None = None
    variable: str = Field(min_length=1, max_length=160)
    value: float | int | str | bool
    unit: UnitCode | None = None
    likelihood_ratio: float | None = Field(default=None, gt=0, le=1_000_000)
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    source: SourceReference | None = None

    @field_validator("observed_at")
    @classmethod
    def aware_observed_at(cls, value: datetime | None) -> datetime | None:
        return require_aware_datetime(value, "observed_at") if value is not None else value


class PestAssessment(TimeStampedContract):
    """Compatibility assessment contract retained while Phase 6 adds richer records."""

    pest_assessment_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    pest_profile_id: str = Field(min_length=1, max_length=160)
    assessed_at: datetime
    outbreak_probability: float = Field(ge=0, le=1)
    severity_if_outbreak: float = Field(ge=0, le=1)
    exposed_palms: int = Field(ge=0, le=10_000_000)
    conditional_loss: float = Field(ge=0)
    expected_loss: float = Field(ge=0)
    loss_unit: UnitCode
    evidence: list[PestEvidence] = Field(default_factory=list, max_length=500)
    symptoms_to_inspect: list[str] = Field(default_factory=list, max_length=100)
    recommended_inspection_at: datetime | None = None
    quarantine_warning: str | None = Field(default=None, max_length=2000)
    provenance: RunProvenance

    @field_validator("assessed_at", "recommended_inspection_at")
    @classmethod
    def aware_datetimes(cls, value: datetime | None, info):
        return require_aware_datetime(value, info.field_name) if value is not None else value

    @model_validator(mode="after")
    def validate_losses(self) -> "PestAssessment":
        if self.expected_loss > self.conditional_loss + 1e-9:
            raise ValueError("expected_loss cannot exceed conditional_loss")
        if self.loss_unit not in {UnitCode.COUNT, UnitCode.KILOGRAM, UnitCode.TONNE, UnitCode.PHILIPPINE_PESO}:
            raise ValueError("Pest loss must use count, mass, or currency units")
        return self


class PestObservation(TimeStampedContract):
    observation_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    production_forecast_id: UUID | None = None
    pest_profile_id: str = Field(min_length=1, max_length=160)
    factor_code: str = Field(min_length=1, max_length=160)
    evidence_status: EvidenceStatus
    observed_at: datetime
    value: float | int | str | bool
    unit: UnitCode | None = None
    prevalence_fraction: float | None = Field(default=None, ge=0, le=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    source_label: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("observed_at")
    @classmethod
    def aware_observed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "observed_at")

    @model_validator(mode="after")
    def validate_coordinates(self) -> "PestObservation":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        if self.prevalence_fraction is not None and self.production_forecast_id is None:
            raise ValueError("production_forecast_id is required when prevalence_fraction is provided")
        return self


class NearbyConfirmedPestCase(StrictModel):
    pest_profile_id: str = Field(min_length=1, max_length=160)
    distance_m: float = Field(ge=0, le=100_000)
    outbreak_probability: float = Field(default=1.0, ge=0, le=1)
    evidence_status: EvidenceStatus = EvidenceStatus.FIELD_CONFIRMED
    observed_at: datetime | None = None

    @field_validator("observed_at")
    @classmethod
    def aware_observed_at(cls, value: datetime | None) -> datetime | None:
        return require_aware_datetime(value, "observed_at") if value is not None else value


class PestFarmContext(StrictModel):
    total_palms: int = Field(ge=1, le=10_000_000)
    young_palms: int = Field(default=0, ge=0, le=10_000_000)
    healthy_bearing_palms: int = Field(default=0, ge=0, le=10_000_000)
    aging_palms: int = Field(default=0, ge=0, le=10_000_000)
    stressed_palms: int = Field(default=0, ge=0, le=10_000_000)
    infested_or_diseased_palms: int = Field(default=0, ge=0, le=10_000_000)
    rehabilitating_palms: int = Field(default=0, ge=0, le=10_000_000)
    dead_palms: int = Field(default=0, ge=0, le=10_000_000)
    mean_palm_age_years: float | None = Field(default=None, ge=0, le=150)
    maintenance_quality: float = Field(default=0.5, ge=0, le=1)
    sanitation_quality: float = Field(default=0.5, ge=0, le=1)
    drainage_quality: float = Field(default=0.5, ge=0, le=1)
    waterlogging: bool = False
    natural_enemies_present: bool = False
    decaying_organic_breeding_material: bool = False
    fresh_palm_wounds: bool = False
    storm_damage: bool = False
    symptom_codes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_counts(self) -> "PestFarmContext":
        counted = (
            self.young_palms + self.healthy_bearing_palms + self.aging_palms + self.stressed_palms
            + self.infested_or_diseased_palms + self.rehabilitating_palms + self.dead_palms
        )
        if counted > self.total_palms:
            raise ValueError("Palm-state counts cannot exceed total_palms")
        return self


class PestAssessmentRequest(VersionedContract):
    farm_id: UUID
    cell_id: UUID | None = None
    production_forecast_id: UUID
    posterior_id: UUID | None = None
    pest_profile_ids: list[str] = Field(default_factory=list, max_length=20)
    assessed_at: datetime
    context: PestFarmContext
    observation_ids: list[UUID] = Field(default_factory=list, max_length=500)
    nearby_confirmed_cases: list[NearbyConfirmedPestCase] = Field(default_factory=list, max_length=500)
    farm_data_version: str = Field(min_length=1, max_length=120)

    @field_validator("assessed_at")
    @classmethod
    def aware_assessed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "assessed_at")


class PestEvidenceContribution(StrictModel):
    sequence: int = Field(ge=1)
    factor_code: str = Field(min_length=1, max_length=160)
    source_kind: PestContributionSource
    direction: PestDirection
    matched: bool
    likelihood_ratio: float = Field(gt=0, le=1_000_000)
    log_odds_delta: float = Field(ge=-50, le=50)
    confidence: ConfidenceLevel
    evidence_status: EvidenceStatus | None = None
    explanation: str = Field(min_length=1, max_length=2000)
    source_document_id: str | None = Field(default=None, max_length=160)
    source_page: int | None = Field(default=None, ge=1)


class PestManagementAction(StrictModel):
    sequence: int = Field(ge=1)
    action_type: str = Field(min_length=1, max_length=120)
    timing: str | None = Field(default=None, max_length=120)
    action_text: str = Field(min_length=1, max_length=2000)
    safety_notes: str | None = Field(default=None, max_length=2000)
    source_document_id: str = Field(min_length=1, max_length=160)
    source_page: int = Field(ge=1)


class PestProfileSnapshot(StrictModel):
    pest_profile_id: str
    common_name: str
    scientific_name: str | None = None
    profile_type: Literal["insect", "disease"]
    reference_confidence: ConfidenceLevel
    source_document_id: str
    source_page: int = Field(ge=1)
    notes: str | None = None


class PestProfileAssessment(TimeStampedContract):
    assessment_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    farm_id: UUID
    cell_id: UUID | None = None
    production_forecast_id: UUID
    posterior_id: UUID | None = None
    assessed_at: datetime
    profile: PestProfileSnapshot
    outbreak_probability: float = Field(ge=0, le=1)
    risk_class: PestRiskClass
    severity_if_outbreak: float = Field(ge=0, le=1)
    exposed_palms: int = Field(ge=0, le=10_000_000)
    conditional_loss: float = Field(ge=0)
    expected_loss: float = Field(ge=0)
    loss_unit: UnitCode = UnitCode.TONNE
    spatial_pressure: float = Field(ge=0, le=1)
    evidence_contributions: list[PestEvidenceContribution] = Field(default_factory=list, max_length=1000)
    symptoms_to_inspect: list[str] = Field(default_factory=list, max_length=100)
    management_actions: list[PestManagementAction] = Field(default_factory=list, max_length=100)
    recommended_inspection_at: datetime
    quarantine_warning: str | None = Field(default=None, max_length=2000)
    provenance: RunProvenance

    @field_validator("assessed_at", "recommended_inspection_at")
    @classmethod
    def aware_dates(cls, value: datetime, info):
        return require_aware_datetime(value, info.field_name)

    @model_validator(mode="after")
    def validate_loss_identity(self) -> "PestProfileAssessment":
        expected = self.outbreak_probability * self.conditional_loss
        tolerance = max(1e-8, abs(expected) * 1e-7)
        if abs(self.expected_loss - expected) > tolerance:
            raise ValueError("expected_loss must equal outbreak_probability × conditional_loss")
        return self


class PestAssessmentSummary(StrictModel):
    highest_probability: float = Field(ge=0, le=1)
    highest_risk_pest_id: str | None = None
    combined_expected_loss_tonnes: float = Field(ge=0)
    urgent_inspection_count: int = Field(ge=0)
    confirmed_evidence_count: int = Field(ge=0)


class PestEngineOutput(VersionedContract):
    run_id: UUID
    assessments: list[PestProfileAssessment] = Field(min_length=1, max_length=20)
    summary: PestAssessmentSummary
    parameter_version: str
    data_notice: str
    warnings: list[str] = Field(default_factory=list, max_length=100)
    taxonomy_notice: str
    weather_feature_set_id: UUID
    weather_run_id: UUID
    evidence_audit: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
