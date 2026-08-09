from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import DataQualityFlag, ForecastHorizonType, ProductType
from app.domain.provenance import RunProvenance
from app.domain.units import UnitCode
from app.domain.weather import MAX_LIVE_FORECAST_DAYS


class LegacyVarietyClass(StrEnum):
    TALL = "Tall"
    DWARF = "Dwarf"
    HYBRID = "Hybrid"
    UNKNOWN = "Unknown"


class LegacyProductionIntervention(StrEnum):
    NONE = "none"
    MONITORING = "monitoring"
    PEST_CONTROL = "pest_control"
    SOIL_REHABILITATION = "soil_rehabilitation"
    REPLANTING = "replanting"
    COMBINED = "combined"


class PredictiveInterval(VersionedContract):
    lower: float = Field(ge=0)
    median: float = Field(ge=0)
    upper: float = Field(ge=0)
    lower_quantile: float = Field(default=0.05, ge=0, le=1)
    upper_quantile: float = Field(default=0.95, ge=0, le=1)

    @model_validator(mode="after")
    def ordered(self) -> "PredictiveInterval":
        if not self.lower <= self.median <= self.upper:
            raise ValueError("Predictive interval must satisfy lower <= median <= upper")
        if self.lower_quantile >= self.upper_quantile:
            raise ValueError("lower_quantile must be below upper_quantile")
        return self


class LegacyProductionFeatureSnapshot(TimeStampedContract):
    feature_snapshot_id: UUID = Field(default_factory=uuid4)
    weather_feature_set_id: UUID
    weather_run_id: UUID
    feature_adapter_version: str = Field(min_length=1, max_length=120)
    feature_order: list[str] = Field(min_length=1, max_length=100)
    features: dict[str, float | int | str]
    ordered_values: list[float | int | str] = Field(min_length=1, max_length=100)
    source_map: dict[str, str] = Field(default_factory=dict)
    quality_flags: list[DataQualityFlag] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    feature_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def feature_order_is_exact(self) -> "LegacyProductionFeatureSnapshot":
        if set(self.features) != set(self.feature_order):
            raise ValueError("features must contain exactly the names in feature_order")
        expected_values = [self.features[name] for name in self.feature_order]
        if expected_values != self.ordered_values:
            raise ValueError("ordered_values must follow feature_order exactly")
        canonical = json.dumps(
            {"feature_order": self.feature_order, "ordered_values": self.ordered_values},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != self.feature_sha256:
            raise ValueError("feature_sha256 does not match the ordered feature payload")
        return self


class ProductEstimate(VersionedContract):
    product: ProductType
    quantity: float = Field(ge=0)
    unit: UnitCode
    estimate_kind: Literal["direct_model_output", "variety_conversion", "official_share_split"]
    conversion_basis: str = Field(min_length=1, max_length=500)
    parameter_names: list[str] = Field(default_factory=list, max_length=50)
    quality_flags: list[DataQualityFlag] = Field(default_factory=list)


class ProductionShadowComparison(VersionedContract):
    status: Literal["available", "not_available"]
    legacy_prediction_tons: float | None = Field(default=None, ge=0)
    v3_raw_prediction_tons: float = Field(ge=0)
    v3_variety_adjusted_prediction_tons: float = Field(ge=0)
    raw_delta_tons: float | None = None
    adjusted_delta_tons: float | None = None
    legacy_method: str = Field(min_length=1, max_length=500)


class ProductionForecast(TimeStampedContract):
    production_forecast_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    product: ProductType
    horizon_type: ForecastHorizonType
    valid_from: datetime
    valid_to: datetime
    estimate_period: Literal["annualized"] = "annualized"
    unit: UnitCode
    raw_ml_prediction: float | None = Field(default=None, ge=0)
    variety_adjusted_prediction: float | None = Field(default=None, ge=0)
    posterior_prediction: PredictiveInterval | None = None
    posterior_status: Literal["not_run", "available"] = "not_run"
    probability_of_decline: float | None = Field(default=None, ge=0, le=1)
    model_version: str = Field(min_length=1, max_length=120)
    feature_adapter_version: str = Field(min_length=1, max_length=120)
    feature_snapshot_id: UUID | None = None
    variety_id: str | None = Field(default=None, max_length=160)
    variety_class: LegacyVarietyClass = LegacyVarietyClass.UNKNOWN
    variety_adjustment_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    variety_adjustment_basis: str = Field(default="No named-variety adjustment was applied.", min_length=1, max_length=1000)
    product_estimates: list[ProductEstimate] = Field(default_factory=list, max_length=30)
    provenance: RunProvenance

    @field_validator("valid_from", "valid_to")
    @classmethod
    def aware_datetimes(cls, value: datetime, info):
        return require_aware_datetime(value, info.field_name)

    @model_validator(mode="after")
    def validate_forecast(self) -> "ProductionForecast":
        if self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be before valid_from")
        if self.horizon_type == ForecastHorizonType.LIVE_NUMERICAL and self.valid_to - self.valid_from > timedelta(days=MAX_LIVE_FORECAST_DAYS):
            raise ValueError(f"Live numerical forecast horizon may not exceed {MAX_LIVE_FORECAST_DAYS} days")
        if self.unit not in {UnitCode.COUNT, UnitCode.KILOGRAM, UnitCode.TONNE, UnitCode.KILOGRAM_PER_HECTARE, UnitCode.TONNE_PER_HECTARE}:
            raise ValueError("Production forecasts must use count, mass, or yield units")
        if self.posterior_prediction is not None and self.posterior_status == "not_run":
            # Preserve Phase 1 contract compatibility: supplying a posterior implies it is available.
            object.__setattr__(self, "posterior_status", "available")
        if self.posterior_status == "available" and self.posterior_prediction is None:
            raise ValueError("posterior_prediction is required when posterior_status is available")
        return self


class ProductionEngineRequest(VersionedContract):
    farm_id: UUID
    cell_id: UUID | None = None
    farm_data_version: str = Field(default="farm-profile-1", min_length=1, max_length=120)
    weather_feature_set_id: UUID
    farm_area_hectares: float = Field(gt=0, le=100_000)
    productive_trees: int = Field(ge=0, le=10_000_000)
    aging_trees: int = Field(ge=0, le=10_000_000)
    stressed_trees: int = Field(ge=0, le=10_000_000)
    infested_trees: int = Field(ge=0, le=10_000_000)
    recovering_trees: int = Field(ge=0, le=10_000_000)
    soil_ph: float = Field(ge=2.5, le=10)
    nitrogen_index: float = Field(ge=0, le=1)
    phosphorus_index: float = Field(ge=0, le=1)
    potassium_index: float = Field(ge=0, le=1)
    suitability_score: float = Field(ge=0, le=1)
    pest_probability: float = Field(ge=0, le=1)
    variety_id: str | None = Field(default=None, min_length=1, max_length=160)
    variety_class: LegacyVarietyClass = LegacyVarietyClass.UNKNOWN
    intervention: LegacyProductionIntervention = LegacyProductionIntervention.NONE
    baseline_annual_production_tons: float | None = Field(default=None, gt=0, le=1_000_000)
    young_nut_share: float = Field(default=0.03, ge=0, le=1)

    @model_validator(mode="after")
    def tree_population_nonzero(self) -> "ProductionEngineRequest":
        total = self.productive_trees + self.aging_trees + self.stressed_trees + self.infested_trees + self.recovering_trees
        if total <= 0:
            raise ValueError("At least one non-dead palm must be supplied")
        return self


class ProductionEngineOutput(VersionedContract):
    forecast: ProductionForecast
    feature_snapshot: LegacyProductionFeatureSnapshot
    shadow_comparison: ProductionShadowComparison
    data_notice: str = Field(min_length=1, max_length=2000)
    warnings: list[str] = Field(default_factory=list, max_length=100)


class ProductionActualInput(VersionedContract):
    farm_id: UUID
    forecast_id: UUID | None = None
    product: ProductType
    period_start: datetime
    period_end: datetime
    quantity: float = Field(ge=0)
    unit: UnitCode
    source_type: Literal["measured", "farmer_reported", "government_record"]
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("period_start", "period_end")
    @classmethod
    def aware_periods(cls, value: datetime, info):
        return require_aware_datetime(value, info.field_name)

    @model_validator(mode="after")
    def period_is_ordered(self) -> "ProductionActualInput":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        if self.unit not in {UnitCode.COUNT, UnitCode.KILOGRAM, UnitCode.TONNE, UnitCode.KILOGRAM_PER_HECTARE, UnitCode.TONNE_PER_HECTARE}:
            raise ValueError("Production actuals must use count, mass, or yield units")
        return self
