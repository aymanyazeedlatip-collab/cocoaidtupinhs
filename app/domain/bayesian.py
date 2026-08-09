from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import EvidenceStatus
from app.domain.production import LegacyProductionIntervention, PredictiveInterval
from app.domain.provenance import RunProvenance
from app.domain.units import UnitCode


class PalmStateVector(VersionedContract):
    young: int = Field(ge=0)
    healthy_bearing: int = Field(ge=0)
    aging: int = Field(ge=0)
    stressed: int = Field(ge=0)
    infested_or_diseased: int = Field(ge=0)
    rehabilitating: int = Field(ge=0)
    dead: int = Field(ge=0)
    soil_fertility_index: float = Field(ge=0, le=1)
    soil_water_index: float = Field(ge=0, le=1)

    @property
    def total_palms(self) -> int:
        return (
            self.young
            + self.healthy_bearing
            + self.aging
            + self.stressed
            + self.infested_or_diseased
            + self.rehabilitating
            + self.dead
        )


class PosteriorParameter(VersionedContract):
    name: str = Field(min_length=1, max_length=160)
    distribution: str = Field(min_length=1, max_length=80)
    parameters: dict[str, float] = Field(min_length=1)
    posterior_mean: float | None = None
    credible_interval: PredictiveInterval | None = None


class BayesianEvidenceType(StrEnum):
    HARVEST = "harvest"
    PEST_PREVALENCE = "pest_prevalence"
    TREE_MORTALITY = "tree_mortality"
    STORM_DAMAGE = "storm_damage"
    REHABILITATION_COMPLETION = "rehabilitation_completion"
    ACTUAL_RAINFALL = "actual_rainfall"


_EVIDENCE_UNITS: dict[BayesianEvidenceType, set[UnitCode]] = {
    BayesianEvidenceType.HARVEST: {UnitCode.KILOGRAM, UnitCode.TONNE},
    BayesianEvidenceType.PEST_PREVALENCE: {UnitCode.FRACTION, UnitCode.PERCENT, UnitCode.PROBABILITY},
    BayesianEvidenceType.TREE_MORTALITY: {UnitCode.COUNT},
    BayesianEvidenceType.STORM_DAMAGE: {UnitCode.FRACTION, UnitCode.PERCENT, UnitCode.PROBABILITY},
    BayesianEvidenceType.REHABILITATION_COMPLETION: {UnitCode.FRACTION, UnitCode.PERCENT, UnitCode.PROBABILITY},
    BayesianEvidenceType.ACTUAL_RAINFALL: {UnitCode.MILLIMETER},
}


class BayesianEvidenceObservation(TimeStampedContract):
    observation_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    production_forecast_id: UUID | None = None
    evidence_type: BayesianEvidenceType
    evidence_status: EvidenceStatus
    observed_at: datetime
    value: float = Field(ge=0)
    unit: UnitCode
    notes: str | None = Field(default=None, max_length=3000)
    source_label: str | None = Field(default=None, max_length=240)

    @field_validator("observed_at")
    @classmethod
    def aware_observed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "observed_at")

    @model_validator(mode="after")
    def validate_value_and_unit(self) -> "BayesianEvidenceObservation":
        allowed = _EVIDENCE_UNITS[self.evidence_type]
        if self.unit not in allowed:
            raise ValueError(
                f"{self.evidence_type.value} evidence requires one of: "
                + ", ".join(sorted(unit.value for unit in allowed))
            )
        if self.evidence_type in {
            BayesianEvidenceType.PEST_PREVALENCE,
            BayesianEvidenceType.STORM_DAMAGE,
            BayesianEvidenceType.REHABILITATION_COMPLETION,
        }:
            ceiling = 100.0 if self.unit == UnitCode.PERCENT else 1.0
            if self.value > ceiling:
                raise ValueError(f"{self.evidence_type.value} evidence exceeds the valid {self.unit.value} range")
        return self


class StatePosteriorInterval(VersionedContract):
    state_variable: Literal[
        "young", "healthy_bearing", "aging", "stressed", "infested_or_diseased",
        "rehabilitating", "dead", "soil_fertility_index", "soil_water_index",
    ]
    unit: UnitCode
    interval: PredictiveInterval


class EvidenceAssimilationResult(VersionedContract):
    observation_id: UUID
    evidence_type: BayesianEvidenceType
    evidence_status: EvidenceStatus
    used_for_update: bool
    reliability_weight: float = Field(ge=0, le=1)
    effective_sample_size_before: float | None = Field(default=None, ge=0)
    effective_sample_size_after: float | None = Field(default=None, ge=0)
    resampled: bool = False
    explanation: str = Field(min_length=1, max_length=1000)


class BayesianDiagnostics(VersionedContract):
    particle_count: int = Field(ge=1)
    horizon_months: int = Field(ge=1)
    random_seed: int
    prior_posterior_id: UUID | None = None
    evidence_count_requested: int = Field(ge=0)
    evidence_count_used: int = Field(ge=0)
    resampling_count: int = Field(ge=0)
    minimum_effective_sample_size: float = Field(ge=0)
    palm_count_conserved: bool
    deterministic_with_seed: bool = True
    posterior_method: str = "sequential_importance_resampling_particle_filter"


class BayesianSimulationRequest(VersionedContract):
    production_forecast_id: UUID
    initial_state: PalmStateVector | None = None
    prior_posterior_id: UUID | None = None
    baseline_state_date: datetime
    horizon_months: int = Field(default=12, ge=1, le=60)
    particle_count: int = Field(default=1000, ge=100, le=5000)
    random_seed: int = Field(default=20260803, ge=0, le=2_147_483_647)
    intervention: LegacyProductionIntervention = LegacyProductionIntervention.NONE
    evidence_observation_ids: list[UUID] = Field(default_factory=list, max_length=1000)
    farm_data_version: str = Field(default="farm-profile-1", min_length=1, max_length=120)

    @field_validator("baseline_state_date")
    @classmethod
    def aware_baseline_state_date(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "baseline_state_date")

    @model_validator(mode="after")
    def require_exactly_one_state_source(self) -> "BayesianSimulationRequest":
        if (self.initial_state is None) == (self.prior_posterior_id is None):
            raise ValueError("Supply exactly one of initial_state or prior_posterior_id")
        if len(set(self.evidence_observation_ids)) != len(self.evidence_observation_ids):
            raise ValueError("evidence_observation_ids must not contain duplicates")
        return self


class BayesianPosterior(TimeStampedContract):
    posterior_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    production_forecast_id: UUID | None = None
    prior_posterior_id: UUID | None = None
    valid_at: datetime
    horizon_months: int = Field(default=12, ge=1, le=60)
    state: PalmStateVector
    state_intervals: list[StatePosteriorInterval] = Field(default_factory=list, max_length=20)
    parameters: list[PosteriorParameter] = Field(default_factory=list, max_length=500)
    production_distribution: PredictiveInterval
    base_production_tonnes: float | None = Field(default=None, ge=0)
    probability_of_decline: float = Field(ge=0, le=1)
    probability_of_recovery: float = Field(ge=0, le=1)
    probability_of_tree_mortality: float = Field(ge=0, le=1)
    probability_of_pest_outbreak: float = Field(ge=0, le=1)
    primary_uncertainty_sources: list[str] = Field(default_factory=list, max_length=20)
    evidence_observation_ids: list[UUID] = Field(default_factory=list, max_length=10_000)
    provenance: RunProvenance

    @field_validator("valid_at")
    @classmethod
    def aware_valid_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "valid_at")

    @model_validator(mode="after")
    def require_valid_state(self) -> "BayesianPosterior":
        if self.state.total_palms <= 0:
            raise ValueError("Bayesian posterior state must contain at least one palm")
        return self


class BayesianEngineOutput(VersionedContract):
    posterior: BayesianPosterior
    evidence_results: list[EvidenceAssimilationResult] = Field(default_factory=list, max_length=1000)
    diagnostics: BayesianDiagnostics
    data_notice: str = Field(min_length=1, max_length=3000)
    warnings: list[str] = Field(default_factory=list, max_length=200)
