from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import StrictModel, TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import ConfidenceLevel, IntercropModelType
from app.domain.provenance import RunProvenance, SourceReference
from app.domain.units import UnitCode

CanopyDesign = Literal["square", "triangular", "rectangular"]
SuitabilityClass = Literal["unsuitable", "low", "moderate", "high", "very_high"]


class IntercropCandidate(VersionedContract):
    candidate_id: str = Field(min_length=1, max_length=160)
    common_name: str = Field(min_length=1, max_length=160)
    scientific_name: str | None = Field(default=None, max_length=240)
    minimum_light_fraction: float = Field(ge=0, le=1)
    maximum_light_fraction: float = Field(ge=0, le=1)
    minimum_rainfall_mm_year: float | None = Field(default=None, ge=0, le=20_000)
    maximum_rainfall_mm_year: float | None = Field(default=None, ge=0, le=20_000)
    minimum_temperature_c: float | None = Field(default=None, ge=-20, le=70)
    maximum_temperature_c: float | None = Field(default=None, ge=-20, le=70)
    minimum_soil_ph: float | None = Field(default=None, ge=0, le=14)
    maximum_soil_ph: float | None = Field(default=None, ge=0, le=14)
    water_demand_class: str | None = Field(default=None, max_length=80)
    root_competition_class: str | None = Field(default=None, max_length=80)
    sources: list[SourceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ranges(self) -> "IntercropCandidate":
        if self.maximum_light_fraction < self.minimum_light_fraction:
            raise ValueError("maximum_light_fraction must be at least minimum_light_fraction")
        for lower, upper, label in (
            (self.minimum_rainfall_mm_year, self.maximum_rainfall_mm_year, "rainfall"),
            (self.minimum_temperature_c, self.maximum_temperature_c, "temperature"),
            (self.minimum_soil_ph, self.maximum_soil_ph, "soil pH"),
        ):
            if lower is not None and upper is not None and upper < lower:
                raise ValueError(f"Maximum {label} must be at least minimum {label}")
        return self


class SuitabilityComponent(VersionedContract):
    factor: str = Field(min_length=1, max_length=160)
    score: float = Field(ge=0, le=1)
    weight: float = Field(gt=0, le=100)
    hard_constraint_passed: bool = True
    explanation: str = Field(min_length=1, max_length=1000)


class IntercropAssessment(TimeStampedContract):
    """Compatibility contract retained from Phase 1."""

    intercrop_assessment_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID
    candidate_id: str = Field(min_length=1, max_length=160)
    model_type: IntercropModelType = IntercropModelType.EVIDENCE_SCORING
    suitability_score: float = Field(ge=0, le=100)
    components: list[SuitabilityComponent] = Field(min_length=1, max_length=100)
    limiting_factors: list[str] = Field(default_factory=list, max_length=30)
    coconut_competition_risk: float = Field(ge=0, le=1)
    pest_conflict_risk: float = Field(ge=0, le=1)
    expected_yield_lower: float | None = Field(default=None, ge=0)
    expected_yield_median: float | None = Field(default=None, ge=0)
    expected_yield_upper: float | None = Field(default=None, ge=0)
    yield_unit: UnitCode | None = None
    planting_window_start: date | None = None
    planting_window_end: date | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    data_quality_notes: list[str] = Field(default_factory=list, max_length=100)
    provenance: RunProvenance

    @model_validator(mode="after")
    def validate_assessment(self) -> "IntercropAssessment":
        if any(not component.hard_constraint_passed for component in self.components) and self.suitability_score > 40:
            raise ValueError("Suitability score may not exceed 40 when a hard constraint fails")
        values = [self.expected_yield_lower, self.expected_yield_median, self.expected_yield_upper]
        if any(value is not None for value in values):
            if not all(value is not None for value in values):
                raise ValueError("Expected yield requires lower, median, and upper values together")
            assert self.expected_yield_lower is not None
            assert self.expected_yield_median is not None
            assert self.expected_yield_upper is not None
            if not self.expected_yield_lower <= self.expected_yield_median <= self.expected_yield_upper:
                raise ValueError("Expected yield must satisfy lower <= median <= upper")
            if self.yield_unit is None:
                raise ValueError("yield_unit is required when expected yield is provided")
        if self.planting_window_start and self.planting_window_end and self.planting_window_end < self.planting_window_start:
            raise ValueError("planting_window_end must not be before planting_window_start")
        return self


class IntercropCellContext(StrictModel):
    cell_id: UUID = Field(default_factory=uuid4)
    label: str = Field(min_length=1, max_length=120)
    area_hectares: float = Field(gt=0, le=100_000)
    palm_age_years: float = Field(ge=0, le=150)
    spacing_x_m: float = Field(gt=0, le=100)
    spacing_y_m: float = Field(gt=0, le=100)
    canopy_design: CanopyDesign
    canopy_density_index: float = Field(default=0.65, ge=0, le=1)
    row_orientation_degrees: float | None = Field(default=None, ge=0, le=360)
    slope_degrees: float = Field(default=0, ge=0, le=90)
    drainage_index: float = Field(default=0.5, ge=0, le=1)
    soil_ph: float = Field(default=6.0, ge=0, le=14)
    soil_moisture_index: float = Field(default=0.5, ge=0, le=1)
    nitrogen_index: float = Field(default=0.5, ge=0, le=1)
    available_space_fraction: float = Field(default=0.6, ge=0, le=1)
    management_feasibility: float = Field(default=0.6, ge=0, le=1)
    market_access_index: float = Field(default=0.5, ge=0, le=1)


class IntercropAssessmentRequest(VersionedContract):
    farm_id: UUID
    production_forecast_id: UUID
    posterior_id: UUID | None = None
    pest_assessment_run_id: UUID | None = None
    assessed_at: datetime
    candidate_ids: list[str] = Field(default_factory=list, max_length=100)
    cells: list[IntercropCellContext] = Field(min_length=1, max_length=500)
    farm_data_version: str = Field(min_length=1, max_length=120)
    include_economic_potential: bool = True

    @field_validator("assessed_at")
    @classmethod
    def aware_assessed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "assessed_at")

    @model_validator(mode="after")
    def unique_cells(self) -> "IntercropAssessmentRequest":
        ids = [cell.cell_id for cell in self.cells]
        if len(ids) != len(set(ids)):
            raise ValueError("cells must have unique cell_id values")
        return self


class CanopyLightEstimate(StrictModel):
    transmitted_light_fraction: float = Field(ge=0, le=1)
    source_parameter_ids: list[str] = Field(min_length=1, max_length=4)
    interpolation_method: str = Field(min_length=1, max_length=240)
    age_adjusted: bool
    density_adjustment_factor: float = Field(gt=0, le=2)
    orientation_adjustment_factor: float = Field(gt=0, le=2)
    understory_solar_radiation_mj_m2_day: float | None = Field(default=None, ge=0)
    confidence: ConfidenceLevel


class IntercropEconomicPotential(StrictModel):
    status: Literal["available", "not_available"]
    gross_revenue_lower_php: float | None = Field(default=None, ge=0)
    gross_revenue_median_php: float | None = Field(default=None, ge=0)
    gross_revenue_upper_php: float | None = Field(default=None, ge=0)
    basis: str = Field(min_length=1, max_length=1000)
    quality_flags: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_values(self) -> "IntercropEconomicPotential":
        values = [self.gross_revenue_lower_php, self.gross_revenue_median_php, self.gross_revenue_upper_php]
        if self.status == "available":
            if any(value is None for value in values):
                raise ValueError("Available economic potential requires lower, median, and upper values")
            assert self.gross_revenue_lower_php is not None
            assert self.gross_revenue_median_php is not None
            assert self.gross_revenue_upper_php is not None
            if not self.gross_revenue_lower_php <= self.gross_revenue_median_php <= self.gross_revenue_upper_php:
                raise ValueError("Economic potential must satisfy lower <= median <= upper")
        return self


class IntercropCandidateSnapshot(StrictModel):
    candidate_id: str
    common_name: str
    scientific_name: str | None = None
    light_group: Literal["A", "B", "C"]
    minimum_light_fraction: float = Field(ge=0, le=1)
    maximum_light_fraction: float = Field(ge=0, le=1)
    reference_confidence: ConfidenceLevel
    requirement_profile_version: str
    requirement_basis: str
    source_document_id: str
    source_page: int = Field(ge=1)


class IntercropCandidateAssessment(TimeStampedContract):
    assessment_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    farm_id: UUID
    cell_id: UUID
    cell_label: str
    production_forecast_id: UUID
    posterior_id: UUID | None = None
    pest_assessment_run_id: UUID | None = None
    assessed_at: datetime
    candidate: IntercropCandidateSnapshot
    suitability_score: float = Field(ge=0, le=100)
    suitability_class: SuitabilityClass
    hard_constraint_passed: bool
    components: list[SuitabilityComponent] = Field(min_length=1, max_length=30)
    limiting_factors: list[str] = Field(default_factory=list, max_length=10)
    canopy_light: CanopyLightEstimate
    coconut_competition_risk: float = Field(ge=0, le=1)
    pest_conflict_risk: float = Field(ge=0, le=1)
    planting_window_start: date | None = None
    planting_window_end: date | None = None
    recommended_layout: str = Field(min_length=1, max_length=1000)
    economic_potential: IntercropEconomicPotential
    confidence: ConfidenceLevel
    data_quality_notes: list[str] = Field(default_factory=list, max_length=100)
    provenance: RunProvenance

    @field_validator("assessed_at")
    @classmethod
    def aware_datetime(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "assessed_at")

    @model_validator(mode="after")
    def hard_constraint_cap(self) -> "IntercropCandidateAssessment":
        if not self.hard_constraint_passed and self.suitability_score > 40:
            raise ValueError("Suitability score may not exceed 40 when a hard constraint fails")
        return self


class IntercropEngineSummary(StrictModel):
    assessed_cell_count: int = Field(ge=1)
    assessed_candidate_count: int = Field(ge=1)
    total_assessment_count: int = Field(ge=1)
    high_or_very_high_count: int = Field(ge=0)
    best_candidate_by_cell: dict[str, str]
    economic_profiles_used: list[str] = Field(default_factory=list)


class IntercropEngineOutput(TimeStampedContract):
    run_id: UUID
    assessments: list[IntercropCandidateAssessment] = Field(min_length=1, max_length=50_000)
    summary: IntercropEngineSummary
    parameter_version: str
    requirement_profile_version: str
    weather_feature_set_id: UUID
    weather_run_id: UUID
    data_notice: str
    warnings: list[str] = Field(default_factory=list, max_length=100)
