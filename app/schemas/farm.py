from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.common import ProvenanceType

CoconutVariety = Literal["Tall", "Dwarf", "Hybrid", "Unknown"]


class FarmLocation(BaseModel):
    region: str = "Region XII"
    province: str = "South Cotabato"
    municipality: str = "Tupi"
    barangay: str = "Palian"
    latitude: float = Field(default=6.334, ge=-90, le=90)
    longitude: float = Field(default=124.952, ge=-180, le=180)
    polygon: list[list[float]] = Field(default_factory=list)

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[list[float]]) -> list[list[float]]:
        if value and len(value) < 3:
            raise ValueError("Farm polygon must be empty or contain at least three vertices")
        if len(value) > 250:
            raise ValueError("Farm polygon may contain at most 250 vertices")
        for point in value:
            if len(point) != 2:
                raise ValueError("Each polygon point must be [latitude, longitude]")
            if not -90 <= point[0] <= 90 or not -180 <= point[1] <= 180:
                raise ValueError("Polygon coordinates are outside valid bounds")
        return value


class TreeStateInput(BaseModel):
    total_trees: int = Field(default=650, ge=1, le=100000)
    young: int = Field(default=70, ge=0)
    productive: int = Field(default=360, ge=0)
    aging: int = Field(default=110, ge=0)
    stressed: int = Field(default=45, ge=0)
    infested: int = Field(default=25, ge=0)
    recovering: int = Field(default=20, ge=0)
    dead: int = Field(default=20, ge=0)
    average_age_years: float = Field(default=34, ge=0, le=120)
    variety: CoconutVariety = "Tall"

    @model_validator(mode="after")
    def validate_counts(self) -> "TreeStateInput":
        subtotal = self.young + self.productive + self.aging + self.stressed + self.infested + self.recovering + self.dead
        if subtotal != self.total_trees:
            raise ValueError(f"Tree-state counts must sum to total_trees ({self.total_trees}); received {subtotal}")
        return self


class ProductionInput(BaseModel):
    annual_production_tons: float = Field(default=16.0, ge=0, le=100000)
    yield_tons_per_hectare: float = Field(default=3.2, ge=0, le=50)
    copra_weight_kg: float | None = Field(default=None, ge=0)
    nut_count: int | None = Field(default=None, ge=0)
    oil_content_percent: float | None = Field(default=None, ge=0, le=100)


class SoilTerrainInput(BaseModel):
    elevation_m: float = Field(default=150, ge=-100, le=5000)
    slope_degrees: float = Field(default=4.5, ge=0, le=90)
    soil_ph: float = Field(default=6.0, ge=2.5, le=10)
    nitrogen_index: float = Field(default=0.62, ge=0, le=1)
    phosphorus_index: float = Field(default=0.55, ge=0, le=1)
    potassium_index: float = Field(default=0.66, ge=0, le=1)
    drainage_index: float = Field(default=0.72, ge=0, le=1)


class SymptomInput(BaseModel):
    yellowing: bool = False
    crown_decline: bool = False
    frond_cuts: bool = False
    visible_scale_insects: bool = False
    rhinoceros_beetle_damage: bool = False
    premature_nut_fall: bool = False
    nearby_reports: bool = False
    severity: int = Field(default=0, ge=0, le=3)


class ManagementInput(BaseModel):
    fertilizer_activity: bool = False
    soil_rehabilitation: bool = False
    pest_control: bool = False
    replanting_percent: float = Field(default=0, ge=0, le=100)
    monitoring_activity: bool = False
    intervention_burden_score: float = Field(default=0, ge=0, le=10)


class HistoricalEvent(BaseModel):
    event_type: Literal[
        "typhoon", "drought", "extreme_rain", "heat_stress", "pest_outbreak",
        "disease_outbreak", "financial_disruption", "other"
    ]
    year: int = Field(ge=1900, le=2100)
    description: str = Field(default="", max_length=500)
    trees_affected: int | None = Field(default=None, ge=0)
    production_loss_percent: float | None = Field(default=None, ge=0, le=100)
    evidence_source: str = Field(default="farmer_reported", max_length=100)
    confidence: Literal["low", "moderate", "high"] = "moderate"


class FarmCreate(BaseModel):
    name: str = Field(default="COCO-AID Demonstration Farm", min_length=1, max_length=120)
    location: FarmLocation = Field(default_factory=FarmLocation)
    area_hectares: float = Field(default=5.0, gt=0, le=10000)
    trees: TreeStateInput = Field(default_factory=TreeStateInput)
    production: ProductionInput = Field(default_factory=ProductionInput)
    soil_terrain: SoilTerrainInput = Field(default_factory=SoilTerrainInput)
    symptoms: SymptomInput = Field(default_factory=SymptomInput)
    management: ManagementInput = Field(default_factory=ManagementInput)
    events: list[HistoricalEvent] = Field(default_factory=list)
    provenance: dict[str, ProvenanceType] = Field(default_factory=dict)


class FarmRecord(FarmCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class FarmPatch(FarmCreate):
    pass
