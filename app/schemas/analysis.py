from __future__ import annotations

from datetime import date
from typing import Literal, Any
from pydantic import BaseModel, Field, model_validator
from app.schemas.common import AnalysisMetadata
from app.schemas.farm import FarmCreate, SymptomInput, SoilTerrainInput

SSPScenario = Literal["ssp126", "ssp245", "ssp370", "ssp585"]
ClimatePeriod = Literal["historical", "2021-2040", "2041-2060", "2061-2080", "2081-2100"]
Intervention = Literal[
    "no_intervention", "monitoring", "pest_management", "soil_rehabilitation",
    "partial_replanting", "combined_rehabilitation"
]


class PestRiskRequest(BaseModel):
    prior_probability: float = Field(default=0.15, gt=0, lt=1)
    symptoms: SymptomInput = Field(default_factory=SymptomInput)
    humidity_percent: float = Field(default=78, ge=0, le=100)
    rainfall_mm_month: float = Field(default=150, ge=0, le=3000)
    average_tree_age: float = Field(default=35, ge=0, le=120)
    confirmed_positive_reports: int = Field(default=0, ge=0)
    confirmed_negative_reports: int = Field(default=0, ge=0)




class PestSpecificRequest(BaseModel):
    farm: FarmCreate = Field(default_factory=FarmCreate)
    temperature_c: float = Field(default=27.0, ge=-10, le=60)
    humidity_percent: float = Field(default=78.0, ge=0, le=100)
    rainfall_mm_week: float = Field(default=35.0, ge=0, le=2500)
    wind_speed_kmh: float = Field(default=12.0, ge=0, le=400)
    farm_condition_score: float = Field(default=0.65, ge=0, le=1)


class SuitabilityRequest(BaseModel):
    soil_terrain: SoilTerrainInput = Field(default_factory=SoilTerrainInput)
    annual_rainfall_mm: float = Field(default=2200, ge=0, le=10000)
    mean_temperature_c: float = Field(default=27, ge=-10, le=60)
    humidity_percent: float = Field(default=78, ge=0, le=100)
    drought_exposure: float = Field(default=0.18, ge=0, le=1)
    climate_stress: float = Field(default=0.15, ge=0, le=1)


class ClimateProjectionRequest(BaseModel):
    latitude: float = Field(default=6.334, ge=-90, le=90)
    longitude: float = Field(default=124.952, ge=-180, le=180)
    scenario: SSPScenario = "ssp245"
    period: ClimatePeriod = "2041-2060"
    model_mode: Literal["multi_model_median", "lower", "upper", "sample"] = "multi_model_median"


class ClimateTrajectoryRequest(BaseModel):
    latitude: float = Field(default=6.334, ge=-90, le=90)
    longitude: float = Field(default=124.952, ge=-180, le=180)
    start_year: int = Field(default=2026, ge=2020, le=2099)
    end_year: int = Field(default=2050, ge=2021, le=2100)
    scenario: SSPScenario = "ssp245"
    seed: int = 42

    @model_validator(mode="after")
    def valid_years(self) -> "ClimateTrajectoryRequest":
        if self.end_year <= self.start_year:
            raise ValueError("end_year must be after start_year")
        return self


class SimulationRequest(BaseModel):
    farm: FarmCreate = Field(default_factory=FarmCreate)
    start_year: int = Field(default=2026, ge=2020, le=2099)
    end_year: int = Field(default=2050, ge=2021, le=2100)
    scenario: SSPScenario = "ssp245"
    intervention: Intervention = "combined_rehabilitation"
    runs: int = Field(default=1000, ge=100, le=5000)
    seed: int = 42
    recovery_threshold_ratio: float = Field(default=0.85, ge=0.1, le=3)
    severe_loss_threshold_ratio: float = Field(default=0.6, ge=0.05, le=1)

    @model_validator(mode="after")
    def valid_years(self) -> "SimulationRequest":
        if self.end_year <= self.start_year:
            raise ValueError("end_year must be after start_year")
        return self


class ScenarioComparisonRequest(BaseModel):
    farm: FarmCreate = Field(default_factory=FarmCreate)
    start_year: int = Field(default=2026, ge=2020, le=2099)
    end_year: int = Field(default=2050, ge=2021, le=2100)
    scenario: SSPScenario = "ssp245"
    runs: int = Field(default=500, ge=100, le=2000)
    seed: int = 42
    recovery_threshold_ratio: float = Field(default=0.85, ge=0.1, le=3)
    severe_loss_threshold_ratio: float = Field(default=0.60, ge=0.05, le=1)

    @model_validator(mode="after")
    def valid_years(self) -> "ScenarioComparisonRequest":
        if self.end_year <= self.start_year:
            raise ValueError("end_year must be after start_year")
        return self


class FarmSiteForecastRequest(BaseModel):
    farm: FarmCreate = Field(default_factory=FarmCreate)
    start_year: int = Field(default=2026, ge=2020, le=2049)
    end_year: int = Field(default=2050, ge=2021, le=2050)
    start_date: date | None = None
    scenario: SSPScenario = "ssp245"
    intervention: Intervention = "combined_rehabilitation"
    runs: int = Field(default=500, ge=100, le=5000)
    seed: int = 42
    include_live_short_term: bool = True
    recovery_threshold_ratio: float = Field(default=0.85, ge=0.1, le=3)
    severe_loss_threshold_ratio: float = Field(default=0.60, ge=0.05, le=1)

    @model_validator(mode="after")
    def valid_years(self) -> "FarmSiteForecastRequest":
        if self.end_year <= self.start_year:
            raise ValueError("end_year must be after start_year")
        if self.start_date is not None:
            if self.start_date.year != self.start_year:
                raise ValueError("start_date must fall within start_year")
            if self.start_date > date(self.end_year, 12, 31):
                raise ValueError("start_date must not be after the simulation horizon")
        return self


class RehabilitationHazardInput(BaseModel):
    event_type: Literal["typhoon", "drought", "extreme_rain", "heat_stress", "heavy_rain_forecast", "rain_forecast", "other"] = "other"
    label: str = Field(default="Weather-related farm stress", min_length=1, max_length=160)
    start_date: date
    end_date: date
    peak_severity: float = Field(default=0.5, ge=0, le=1)
    estimated_production_loss_tons: float = Field(default=0, ge=0, le=100000)
    loss_percent_of_event_baseline: float = Field(default=0, ge=0, le=100)
    estimated_trees_affected: int = Field(default=0, ge=0, le=100000)
    data_mode: str | None = Field(default=None, max_length=120)
    confidence: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def valid_dates(self) -> "RehabilitationHazardInput":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class RehabilitationPlanRequest(BaseModel):
    farm: FarmCreate = Field(default_factory=FarmCreate)
    hazards: list[RehabilitationHazardInput] = Field(default_factory=list, max_length=60)
    rows: int = Field(default=12, ge=6, le=24)
    cols: int = Field(default=12, ge=6, le=24)
    assessment_delay_days: int = Field(default=3, ge=0, le=30)
    rehabilitation_delay_days: int = Field(default=7, ge=1, le=60)


class FullAnalysisRequest(BaseModel):
    farm: FarmCreate = Field(default_factory=FarmCreate)
    scenario: SSPScenario = "ssp245"
    period: ClimatePeriod = "2041-2060"
    end_year: int = Field(default=2050, ge=2027, le=2100)
    runs: int = Field(default=1000, ge=100, le=5000)
    seed: int = 42
    recovery_threshold_ratio: float = Field(default=0.85, ge=0.1, le=3)
    severe_loss_threshold_ratio: float = Field(default=0.60, ge=0.05, le=1)


class AnalysisRecord(BaseModel):
    id: str
    created_at: str
    input: dict[str, Any]
    result: dict[str, Any]
    metadata: AnalysisMetadata


class ReportRequest(BaseModel):
    analysis_id: str | None = None
    analysis: dict[str, Any] | None = None
    report_format: Literal["pdf", "docx"] = "pdf"

    @model_validator(mode="after")
    def require_source(self) -> "ReportRequest":
        if not self.analysis_id and not self.analysis:
            raise ValueError("analysis_id or analysis must be provided")
        return self


class ForecastSaveRequest(BaseModel):
    name: str = Field(default="Saved COCO-AID forecast", min_length=1, max_length=160)
    farm_id: str | None = None
    forecast_id: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    forecast: dict[str, Any]

    @model_validator(mode="after")
    def validate_forecast_payload(self) -> "ForecastSaveRequest":
        frames = self.forecast.get("frames")
        if isinstance(frames, list) and len(frames) > 2500:
            raise ValueError("forecast contains too many timeline frames; maximum is 2500")

        # Prevent accidental or malicious writes of extremely large JSON blobs while
        # keeping the complete weekly 2026–2050 forecast comfortably below the limit.
        import json

        encoded_size = len(json.dumps(self.forecast, separators=(",", ":"), default=str).encode("utf-8"))
        if encoded_size > 20 * 1024 * 1024:
            raise ValueError("forecast payload exceeds the 20 MB storage limit")
        return self
