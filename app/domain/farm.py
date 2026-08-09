from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from app.domain.base import TimeStampedContract, VersionedContract, require_aware_datetime
from app.domain.enums import ObservationType, PalmState, ProductType
from app.domain.provenance import DataProvenance
from app.domain.units import UnitCode


class GeoPoint(VersionedContract):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FarmBoundary(VersionedContract):
    vertices: list[GeoPoint] = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def validate_unique_vertices(self) -> "FarmBoundary":
        unique = {(point.latitude, point.longitude) for point in self.vertices}
        if len(unique) < 3:
            raise ValueError("Farm boundary must contain at least three unique vertices")
        return self


class FarmLocation(VersionedContract):
    region: str = Field(min_length=1, max_length=160)
    province: str = Field(min_length=1, max_length=160)
    municipality: str = Field(min_length=1, max_length=160)
    barangay: str = Field(min_length=1, max_length=160)
    centroid: GeoPoint
    boundary: FarmBoundary | None = None


class FarmProfile(TimeStampedContract):
    farm_id: UUID = Field(default_factory=uuid4)
    pseudonymous_farmer_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    location: FarmLocation
    area_hectares: float = Field(gt=0, le=100_000)
    declared_coconut_area_hectares: float | None = Field(default=None, ge=0, le=100_000)
    data_version: str = Field(default="farm-profile-1", min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=50)
    provenance: list[DataProvenance] = Field(default_factory=list)

    @model_validator(mode="after")
    def coconut_area_not_larger_than_farm(self) -> "FarmProfile":
        if self.declared_coconut_area_hectares is not None and self.declared_coconut_area_hectares > self.area_hectares:
            raise ValueError("declared_coconut_area_hectares cannot exceed area_hectares")
        return self


class FarmCell(TimeStampedContract):
    cell_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    label: str = Field(min_length=1, max_length=120)
    row_index: int | None = Field(default=None, ge=0)
    column_index: int | None = Field(default=None, ge=0)
    area_hectares: float = Field(gt=0, le=100_000)
    centroid: GeoPoint
    boundary: FarmBoundary | None = None
    elevation_m: float | None = Field(default=None, ge=-500, le=9000)
    slope_degrees: float | None = Field(default=None, ge=0, le=90)
    drainage_index: float | None = Field(default=None, ge=0, le=1)
    canopy_density_index: float | None = Field(default=None, ge=0, le=1)
    provenance: list[DataProvenance] = Field(default_factory=list)


class TreeCohort(TimeStampedContract):
    cohort_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    state: PalmState
    palm_count: int = Field(ge=0, le=10_000_000)
    variety_id: str = Field(default="unknown", min_length=1, max_length=160)
    mean_age_years: float | None = Field(default=None, ge=0, le=150)
    age_standard_deviation_years: float | None = Field(default=None, ge=0, le=100)
    planting_year: int | None = Field(default=None, ge=1800, le=2200)
    spacing_meters: float | None = Field(default=None, gt=0, le=100)
    provenance: list[DataProvenance] = Field(default_factory=list)


class Measurement(VersionedContract):
    variable: str = Field(min_length=1, max_length=160)
    value: float | int | str | bool | None
    unit: UnitCode | None = None
    uncertainty: float | None = Field(default=None, ge=0)
    method: str | None = Field(default=None, max_length=240)
    quality_notes: list[str] = Field(default_factory=list, max_length=30)


class FarmObservation(TimeStampedContract):
    observation_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    observation_type: ObservationType
    observed_at: datetime
    measurements: list[Measurement] = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)
    provenance: DataProvenance

    @field_validator("observed_at")
    @classmethod
    def aware_observed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value, "observed_at")


class ProductionRecord(TimeStampedContract):
    production_record_id: UUID = Field(default_factory=uuid4)
    farm_id: UUID
    cell_id: UUID | None = None
    product: ProductType
    period_start: date
    period_end: date
    quantity: float = Field(ge=0)
    unit: UnitCode
    harvested_area_hectares: float | None = Field(default=None, gt=0, le=100_000)
    grade_or_class: str | None = Field(default=None, max_length=120)
    provenance: DataProvenance

    @model_validator(mode="after")
    def validate_period_and_unit(self) -> "ProductionRecord":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        allowed = {UnitCode.COUNT, UnitCode.KILOGRAM, UnitCode.TONNE, UnitCode.KILOGRAM_PER_HECTARE, UnitCode.TONNE_PER_HECTARE}
        if self.unit not in allowed:
            raise ValueError("Production records must use count, mass, or yield units")
        return self
