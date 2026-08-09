from __future__ import annotations

from enum import StrEnum


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class EvidenceStatus(StrEnum):
    PREDICTED = "predicted"
    SUSPECTED = "suspected"
    FARMER_REPORTED = "farmer_reported"
    FIELD_CONFIRMED = "field_confirmed"
    EXPERT_CONFIRMED = "expert_confirmed"


class SourceType(StrEnum):
    MEASURED = "measured"
    FARMER_REPORTED = "farmer_reported"
    GOVERNMENT_RECORD = "government_record"
    LABORATORY_TEST = "laboratory_test"
    PUBLIC_RASTER = "public_raster"
    PUBLIC_STATISTIC = "public_statistic"
    WEATHER_PROVIDER = "weather_provider"
    MODEL_OUTPUT = "model_output"
    EXPERT_RULE = "expert_rule"
    PCA_REFERENCE = "pca_reference"
    ESTIMATED = "estimated"
    SYNTHETIC_REFERENCE_BASED = "synthetic_reference_based"
    MISSING = "missing"


class DataQualityFlag(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    MISSING = "missing"
    IMPUTED = "imputed"
    OUTLIER = "outlier"
    STALE = "stale"
    LOW_SPATIAL_RESOLUTION = "low_spatial_resolution"
    LOW_TEMPORAL_RESOLUTION = "low_temporal_resolution"
    REFERENCE_ONLY = "reference_only"
    REQUIRES_EXPERT_REVIEW = "requires_expert_review"


class PalmState(StrEnum):
    YOUNG = "young"
    HEALTHY_BEARING = "healthy_bearing"
    AGING = "aging"
    STRESSED = "stressed"
    INFESTED_OR_DISEASED = "infested_or_diseased"
    REHABILITATING = "rehabilitating"
    DEAD = "dead"


class ProductType(StrEnum):
    WHOLE_NUT_WITH_HUSK = "whole_nut_with_husk"
    MATURE_NUT = "mature_nut"
    YOUNG_NUT = "young_nut"
    COPRA = "copra"
    HUSK = "husk"
    SHELL = "shell"
    MEAT = "meat"
    COCONUT_WATER = "coconut_water"
    VCO_POTENTIAL = "vco_potential"
    TODDY = "toddy"
    SUGAR = "sugar"


class ObservationType(StrEnum):
    TREE_INVENTORY = "tree_inventory"
    HARVEST = "harvest"
    PEST_SYMPTOM = "pest_symptom"
    TREE_DAMAGE = "tree_damage"
    SOIL_TEST = "soil_test"
    MANAGEMENT_ACTION = "management_action"
    WEATHER = "weather"
    FIELD_INSPECTION = "field_inspection"
    OTHER = "other"


class WeatherDataKind(StrEnum):
    OBSERVATION = "observation"
    FORECAST = "forecast"
    HISTORICAL = "historical"
    CLIMATE_CONDITIONED = "climate_conditioned"


class ForecastHorizonType(StrEnum):
    LIVE_NUMERICAL = "live_numerical"
    CLIMATE_CONDITIONED = "climate_conditioned"


class EngineMaturity(StrEnum):
    LEGACY = "legacy"
    CONTRACT_ONLY = "contract_only"
    EXPERIMENTAL = "experimental"
    VALIDATION = "validation"
    PRODUCTION = "production"


class EngineAvailability(StrEnum):
    AVAILABLE = "available"
    PLANNED = "planned"
    DISABLED = "disabled"
    DEGRADED = "degraded"


class IntercropModelType(StrEnum):
    RULE_BASED = "rule_based"
    EVIDENCE_SCORING = "evidence_scoring"
    SUPERVISED_ML = "supervised_ml"


class RehabilitationTiming(StrEnum):
    PRE_EVENT = "pre_event"
    POST_EVENT_INSPECTION = "post_event_inspection"
    POST_CONFIRMATION = "post_confirmation"
    ROUTINE = "routine"


class RehabilitationActionType(StrEnum):
    INSPECT = "inspect"
    MONITOR = "monitor"
    SANITATION = "sanitation"
    REMOVE_BREEDING_MATERIAL = "remove_breeding_material"
    DRAINAGE_IMPROVEMENT = "drainage_improvement"
    ORGANIC_MATTER_APPLICATION = "organic_matter_application"
    FERTILIZER_CORRECTION = "fertilizer_correction"
    PEST_OR_DISEASE_TREATMENT = "pest_or_disease_treatment"
    PRUNING_OR_CROWN_MANAGEMENT = "pruning_or_crown_management"
    PARTIAL_REPLANTING = "partial_replanting"
    COMPLETE_REPLANTING = "complete_replanting"
    VARIETY_REPLACEMENT = "variety_replacement"
    INTERCROPPING_ADJUSTMENT = "intercropping_adjustment"
