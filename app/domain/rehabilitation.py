from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import StrictModel, TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import ConfidenceLevel, EvidenceStatus, RehabilitationActionType, RehabilitationTiming
from app.domain.provenance import RunProvenance
from app.domain.units import UnitCode

ScenarioType = Literal[
    "no_action",
    "pest_management",
    "fertilization",
    "replanting",
    "intercropping",
    "combined_rehabilitation",
]
ScenarioStatus = Literal["feasible", "infeasible_budget", "infeasible_labor", "not_applicable"]
PriorityClass = Literal["routine", "low", "moderate", "high", "critical"]
TriggerSource = Literal["farm_context", "production", "bayesian", "pest", "intercropping", "weather"]


class CostEstimate(VersionedContract):
    materials_php: float = Field(default=0, ge=0)
    labor_php: float = Field(default=0, ge=0)
    other_php: float = Field(default=0, ge=0)
    total_php: float = Field(ge=0)
    labor_person_days: float | None = Field(default=None, ge=0)
    basis: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def total_matches_components(self) -> "CostEstimate":
        component_total = self.materials_php + self.labor_php + self.other_php
        tolerance = max(0.01, component_total * 0.001)
        if abs(self.total_php - component_total) > tolerance:
            raise ValueError("total_php must equal materials_php + labor_php + other_php")
        return self


class RehabilitationTrigger(VersionedContract):
    trigger_code: str = Field(min_length=1, max_length=120)
    source: TriggerSource
    severity: float = Field(ge=0, le=1)
    evidence_status: EvidenceStatus | None = None
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=100)
    description: str = Field(min_length=1, max_length=1200)
    confirmed_damage: bool = False

    @model_validator(mode="after")
    def predicted_is_not_confirmed(self) -> "RehabilitationTrigger":
        if self.evidence_status in {EvidenceStatus.PREDICTED, EvidenceStatus.SUSPECTED} and self.confirmed_damage:
            raise ValueError("Predicted or suspected evidence cannot be marked as confirmed damage")
        return self


class RehabilitationCellContext(StrictModel):
    cell_id: UUID = Field(default_factory=uuid4)
    label: str = Field(min_length=1, max_length=160)
    area_hectares: float = Field(gt=0, le=100_000)
    total_palms: int = Field(ge=1, le=10_000_000)
    young_palms: int = Field(default=0, ge=0)
    healthy_bearing_palms: int = Field(default=0, ge=0)
    aging_palms: int = Field(default=0, ge=0)
    stressed_palms: int = Field(default=0, ge=0)
    infested_or_diseased_palms: int = Field(default=0, ge=0)
    rehabilitating_palms: int = Field(default=0, ge=0)
    dead_palms: int = Field(default=0, ge=0)
    drainage_index: float = Field(default=0.5, ge=0, le=1)
    soil_fertility_index: float = Field(default=0.5, ge=0, le=1)
    soil_water_index: float = Field(default=0.5, ge=0, le=1)
    production_decline_fraction: float = Field(default=0, ge=0, le=1)
    nutrient_deficiency_status: EvidenceStatus | None = None
    storm_damage_status: EvidenceStatus | None = None
    sanitation_quality: float = Field(default=0.5, ge=0, le=1)
    access_feasibility: float = Field(default=0.7, ge=0, le=1)

    @model_validator(mode="after")
    def palm_counts_fit_total(self) -> "RehabilitationCellContext":
        state_sum = sum((
            self.young_palms, self.healthy_bearing_palms, self.aging_palms,
            self.stressed_palms, self.infested_or_diseased_palms,
            self.rehabilitating_palms, self.dead_palms,
        ))
        if state_sum != self.total_palms:
            raise ValueError("Palm-state counts must sum exactly to total_palms")
        return self


class RehabilitationPlanRequest(VersionedContract):
    farm_id: UUID
    production_forecast_id: UUID
    posterior_id: UUID | None = None
    pest_assessment_run_id: UUID | None = None
    intercropping_run_id: UUID | None = None
    planned_at: datetime
    cells: list[RehabilitationCellContext] = Field(min_length=1, max_length=500)
    total_budget_php: float | None = Field(default=None, ge=0)
    available_labor_person_days: float | None = Field(default=None, ge=0)
    planning_horizon_months: int = Field(default=24, ge=1, le=120)
    annual_discount_rate: float = Field(default=0.08, ge=0, le=1)
    risk_aversion: float = Field(default=0.35, ge=0, le=2)
    farm_data_version: str = Field(min_length=1, max_length=120)

    @field_validator("planned_at")
    @classmethod
    def aware_planned_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "planned_at")

    @model_validator(mode="after")
    def unique_cells(self) -> "RehabilitationPlanRequest":
        ids = [cell.cell_id for cell in self.cells]
        if len(ids) != len(set(ids)):
            raise ValueError("cells must have unique cell_id values")
        return self


class RehabilitationAction(VersionedContract):
    action_id: UUID = Field(default_factory=uuid4)
    cell_id: UUID | None = None
    action_type: RehabilitationActionType
    timing: RehabilitationTiming
    priority: PriorityClass = "moderate"
    problem_detected: str = Field(min_length=1, max_length=1000)
    likely_cause: str = Field(min_length=1, max_length=1000)
    triggers: list[RehabilitationTrigger] = Field(default_factory=list, max_length=100)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=1000)
    instructions: list[str] = Field(min_length=1, max_length=100)
    required_materials: list[str] = Field(default_factory=list, max_length=100)
    scheduled_date: date | None = None
    follow_up_dates: list[date] = Field(default_factory=list, max_length=50)
    cost: CostEstimate
    expected_recovery_days: int | None = Field(default=None, ge=0, le=3650)
    expected_production_regained_lower: float | None = Field(default=None, ge=0)
    expected_production_regained_median: float | None = Field(default=None, ge=0)
    expected_production_regained_upper: float | None = Field(default=None, ge=0)
    production_regained_unit: UnitCode | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    requires_field_confirmation: bool = False
    parameter_basis: str = Field(default="Legacy-compatible action without a Phase 8 parameter trace.", min_length=1, max_length=1200)

    @model_validator(mode="after")
    def validate_recovery_unit(self) -> "RehabilitationAction":
        values = [
            self.expected_production_regained_lower,
            self.expected_production_regained_median,
            self.expected_production_regained_upper,
        ]
        if any(value is not None for value in values):
            if not all(value is not None for value in values):
                raise ValueError("Production regained requires lower, median, and upper values together")
            assert self.expected_production_regained_lower is not None
            assert self.expected_production_regained_median is not None
            assert self.expected_production_regained_upper is not None
            if not self.expected_production_regained_lower <= self.expected_production_regained_median <= self.expected_production_regained_upper:
                raise ValueError("Production regained must satisfy lower <= median <= upper")
            if self.production_regained_unit is None:
                raise ValueError("production_regained_unit is required when production regained is provided")
        elif self.production_regained_unit is not None:
            raise ValueError("production_regained_unit requires production regained estimates")
        if self.scheduled_date and any(item < self.scheduled_date for item in self.follow_up_dates):
            raise ValueError("follow_up_dates must not be before scheduled_date")
        return self


class RehabilitationScenarioResult(TimeStampedContract):
    scenario_id: UUID = Field(default_factory=uuid4)
    scenario_type: ScenarioType
    status: ScenarioStatus
    action_ids: list[UUID] = Field(default_factory=list, max_length=10_000)
    total_cost_php: float = Field(ge=0)
    labor_person_days: float = Field(ge=0)
    coconut_production_lower_tonnes: float = Field(ge=0)
    coconut_production_median_tonnes: float = Field(ge=0)
    coconut_production_upper_tonnes: float = Field(ge=0)
    intercrop_gross_revenue_lower_php: float = Field(default=0, ge=0)
    intercrop_gross_revenue_median_php: float = Field(default=0, ge=0)
    intercrop_gross_revenue_upper_php: float = Field(default=0, ge=0)
    severe_loss_probability: float = Field(ge=0, le=1)
    expected_utility: float
    utility_components: dict[str, float] = Field(default_factory=dict)
    feasibility_reasons: list[str] = Field(default_factory=list, max_length=100)
    assumptions: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def valid_ranges(self) -> "RehabilitationScenarioResult":
        if not self.coconut_production_lower_tonnes <= self.coconut_production_median_tonnes <= self.coconut_production_upper_tonnes:
            raise ValueError("Coconut production must satisfy lower <= median <= upper")
        if not self.intercrop_gross_revenue_lower_php <= self.intercrop_gross_revenue_median_php <= self.intercrop_gross_revenue_upper_php:
            raise ValueError("Intercrop revenue must satisfy lower <= median <= upper")
        return self


class RehabilitationPlan(TimeStampedContract):
    rehabilitation_plan_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    analysis_run_id: UUID = Field(default_factory=uuid4)
    production_forecast_id: UUID | None = None
    posterior_id: UUID | None = None
    pest_assessment_run_id: UUID | None = None
    intercropping_run_id: UUID | None = None
    actions: list[RehabilitationAction] = Field(default_factory=list, max_length=10_000)
    scenarios: list[RehabilitationScenarioResult] = Field(default_factory=list, max_length=20)
    selected_scenario: ScenarioType = "no_action"
    total_budget_php: float | None = Field(default=None, ge=0)
    total_expected_cost_php: float = Field(ge=0)
    expected_recovery_summary: str = Field(min_length=1, max_length=5000)
    no_action_comparison_id: UUID | None = None
    unallocated_budget_php: float | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    data_notice: str = Field(default="Legacy-compatible rehabilitation plan contract.", min_length=1, max_length=5000)
    provenance: RunProvenance

    @model_validator(mode="after")
    def validate_totals_and_budget(self) -> "RehabilitationPlan":
        selected = next((item for item in self.scenarios if item.scenario_type == self.selected_scenario), None)
        if selected is not None:
            tolerance = max(0.01, selected.total_cost_php * 0.001)
            if abs(self.total_expected_cost_php - selected.total_cost_php) > tolerance:
                raise ValueError("total_expected_cost_php must match the selected scenario")
        elif self.actions:
            calculated = sum(action.cost.total_php for action in self.actions)
            tolerance = max(0.01, calculated * 0.001)
            if abs(self.total_expected_cost_php - calculated) > tolerance:
                raise ValueError("total_expected_cost_php must equal the sum of action costs")
        if self.total_budget_php is not None and self.total_expected_cost_php > self.total_budget_php + 0.01:
            raise ValueError("Selected rehabilitation scenario exceeds total_budget_php")
        if self.unallocated_budget_php is not None and self.total_budget_php is None:
            raise ValueError("unallocated_budget_php requires total_budget_php")
        return self


class RehabilitationEngineSummary(StrictModel):
    assessed_cell_count: int = Field(ge=1)
    trigger_count: int = Field(ge=0)
    candidate_action_count: int = Field(ge=0)
    feasible_scenario_count: int = Field(ge=1)
    selected_scenario: ScenarioType
    selected_cost_php: float = Field(ge=0)
    selected_labor_person_days: float = Field(ge=0)
    critical_cell_ids: list[UUID] = Field(default_factory=list, max_length=500)
    field_confirmation_required: bool


class RehabilitationEngineOutput(TimeStampedContract):
    plan: RehabilitationPlan
    summary: RehabilitationEngineSummary
    parameter_version: str = Field(min_length=1, max_length=120)
    cost_catalog_version: str = Field(min_length=1, max_length=120)
    linked_weather_run_id: UUID | None = None
    warnings: list[str] = Field(default_factory=list, max_length=100)
