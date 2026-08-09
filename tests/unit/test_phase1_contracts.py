from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.bayesian import BayesianPosterior, PalmStateVector
from app.domain.contract_registry import contract_registry
from app.domain.enums import (
    EvidenceStatus,
    ForecastHorizonType,
    IntercropModelType,
    ObservationType,
    PalmState,
    ProductType,
    RehabilitationActionType,
    RehabilitationTiming,
    SourceType,
    WeatherDataKind,
)
from app.domain.farm import (
    FarmBoundary,
    FarmLocation,
    FarmObservation,
    FarmProfile,
    GeoPoint,
    Measurement,
    ProductionRecord,
    TreeCohort,
)
from app.domain.intercropping import IntercropAssessment, IntercropCandidate, SuitabilityComponent
from app.domain.pest import PestAssessment, PestEvidence
from app.domain.production import PredictiveInterval, ProductionForecast
from app.domain.provenance import DataProvenance, RunProvenance, SourceReference
from app.domain.rehabilitation import CostEstimate, RehabilitationAction, RehabilitationPlan
from app.domain.units import UnitCode, convert_value
from app.domain.weather import WeatherFeature, WeatherFeatureSet, WeatherModelRun, WeatherVariable


def source() -> SourceReference:
    return SourceReference(
        source_id="test-source",
        title="Test field source",
        source_type=SourceType.MEASURED,
        organization="COCOAID tests",
    )


def data_provenance() -> DataProvenance:
    return DataProvenance(source=source(), observed_at=datetime.now(UTC), retrieved_at=datetime.now(UTC))


def run_provenance() -> RunProvenance:
    return RunProvenance(farm_data_version="farm-test-1", simulation_seed=42, simulation_count=1000)


def test_strict_farm_contracts_and_cross_field_validation():
    farm_id = uuid4()
    polygon = FarmBoundary(vertices=[
        GeoPoint(latitude=6.3, longitude=124.9),
        GeoPoint(latitude=6.3, longitude=125.0),
        GeoPoint(latitude=6.4, longitude=125.0),
    ])
    profile = FarmProfile(
        farm_id=farm_id,
        name="Reference Farm",
        location=FarmLocation(
            region="Region XII",
            province="South Cotabato",
            municipality="Tupi",
            barangay="Palian",
            centroid=GeoPoint(latitude=6.334, longitude=124.952),
            boundary=polygon,
        ),
        area_hectares=5,
        declared_coconut_area_hectares=4.5,
        provenance=[data_provenance()],
    )
    assert profile.schema_version == "3.0.0-draft.10"

    cohort = TreeCohort(farm_id=farm_id, state=PalmState.HEALTHY_BEARING, palm_count=350, variety_id="tall")
    assert cohort.palm_count == 350

    observation = FarmObservation(
        farm_id=farm_id,
        observation_type=ObservationType.FIELD_INSPECTION,
        observed_at=datetime.now(UTC),
        measurements=[Measurement(variable="healthy_palms", value=350, unit=UnitCode.COUNT)],
        provenance=data_provenance(),
    )
    assert observation.measurements[0].unit == UnitCode.COUNT

    with pytest.raises(ValidationError, match="declared_coconut_area_hectares"):
        FarmProfile(
            farm_id=farm_id,
            name="Invalid",
            location=profile.location,
            area_hectares=2,
            declared_coconut_area_hectares=3,
        )

    with pytest.raises(ValidationError, match="extra_forbidden"):
        FarmProfile.model_validate({**profile.model_dump(mode="json"), "unexpected": True})


def test_production_record_period_and_units():
    record = ProductionRecord(
        farm_id=uuid4(),
        product=ProductType.COPRA,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        quantity=5.2,
        unit=UnitCode.TONNE,
        provenance=data_provenance(),
    )
    assert record.quantity == 5.2
    with pytest.raises(ValidationError, match="period_end"):
        ProductionRecord(
            farm_id=uuid4(), product=ProductType.COPRA,
            period_start=date(2026, 2, 1), period_end=date(2026, 1, 1),
            quantity=1, unit=UnitCode.TONNE, provenance=data_provenance(),
        )


def test_weather_contract_enforces_16_day_live_forecast_limit_and_units():
    now = datetime.now(UTC)
    run = WeatherModelRun(
        provider="Open-Meteo",
        provider_model="auto",
        data_kind=WeatherDataKind.FORECAST,
        model_run_at=now,
        retrieved_at=now,
        valid_from=now,
        valid_to=now + timedelta(days=16),
        latitude=6.334,
        longitude=124.952,
        variables=[WeatherVariable.PRECIPITATION, WeatherVariable.TEMPERATURE_MEAN],
        units={
            WeatherVariable.PRECIPITATION: UnitCode.MILLIMETER,
            WeatherVariable.TEMPERATURE_MEAN: UnitCode.CELSIUS,
        },
        source=source(),
    )
    feature_set = WeatherFeatureSet(
        weather_run_id=run.weather_run_id,
        farm_id=uuid4(),
        valid_at=now,
        feature_adapter_version="weather-features-0.1",
        features=[WeatherFeature(name="rainfall_30d", value=125, unit=UnitCode.MILLIMETER, aggregation_window_days=30, derivation="rolling sum")],
    )
    assert feature_set.features[0].aggregation_window_days == 30

    with pytest.raises(ValidationError, match="16 days"):
        WeatherModelRun(
            **{**run.model_dump(), "weather_run_id": uuid4(), "valid_to": now + timedelta(days=16, seconds=1)}
        )
    with pytest.raises(ValidationError, match="Missing units"):
        WeatherModelRun(
            **{**run.model_dump(), "weather_run_id": uuid4(), "units": {WeatherVariable.PRECIPITATION: UnitCode.MILLIMETER}}
        )


def test_production_and_bayesian_contracts_separate_live_and_long_term_outputs():
    now = datetime.now(UTC)
    interval = PredictiveInterval(lower=10, median=12, upper=16)
    forecast = ProductionForecast(
        farm_id=uuid4(),
        product=ProductType.WHOLE_NUT_WITH_HUSK,
        horizon_type=ForecastHorizonType.LIVE_NUMERICAL,
        valid_from=now,
        valid_to=now + timedelta(days=16),
        unit=UnitCode.TONNE,
        raw_ml_prediction=12,
        variety_adjusted_prediction=12.5,
        posterior_prediction=interval,
        model_version="production-synthetic-1.0",
        feature_adapter_version="adapter-0.1",
        provenance=run_provenance(),
    )
    assert forecast.posterior_prediction.median == 12

    posterior = BayesianPosterior(
        farm_id=forecast.farm_id,
        valid_at=now,
        state=PalmStateVector(
            young=10, healthy_bearing=80, aging=10, stressed=5,
            infested_or_diseased=2, rehabilitating=1, dead=2,
            soil_fertility_index=0.6, soil_water_index=0.7,
        ),
        production_distribution=interval,
        probability_of_decline=0.2,
        probability_of_recovery=0.7,
        probability_of_tree_mortality=0.05,
        probability_of_pest_outbreak=0.1,
        provenance=run_provenance(),
    )
    assert posterior.state.total_palms == 110

    with pytest.raises(ValidationError, match="lower <= median <= upper"):
        PredictiveInterval(lower=10, median=9, upper=12)


def test_pest_contract_keeps_conditional_and_expected_loss_distinct():
    now = datetime.now(UTC)
    assessment = PestAssessment(
        farm_id=uuid4(),
        pest_profile_id="coconut_scale_insect",
        assessed_at=now,
        outbreak_probability=0.2,
        severity_if_outbreak=0.6,
        exposed_palms=100,
        conditional_loss=10,
        expected_loss=2,
        loss_unit=UnitCode.TONNE,
        evidence=[PestEvidence(
            pest_profile_id="coconut_scale_insect",
            status=EvidenceStatus.FARMER_REPORTED,
            observed_at=now,
            variable="visible_scale",
            value=True,
        )],
        provenance=run_provenance(),
    )
    assert assessment.expected_loss < assessment.conditional_loss
    with pytest.raises(ValidationError, match="expected_loss cannot exceed"):
        PestAssessment(**{**assessment.model_dump(), "pest_assessment_id": uuid4(), "expected_loss": 11})


def test_intercrop_contract_applies_hard_constraint_ceiling():
    candidate = IntercropCandidate(
        candidate_id="cacao",
        common_name="Cacao",
        scientific_name="Theobroma cacao",
        minimum_light_fraction=0.2,
        maximum_light_fraction=0.6,
    )
    assert candidate.maximum_light_fraction == 0.6
    component = SuitabilityComponent(factor="light", score=0.2, weight=3, hard_constraint_passed=False, explanation="Insufficient light")
    assessment = IntercropAssessment(
        farm_id=uuid4(), cell_id=uuid4(), candidate_id="cacao",
        model_type=IntercropModelType.EVIDENCE_SCORING,
        suitability_score=35,
        components=[component],
        limiting_factors=["light"],
        coconut_competition_risk=0.1,
        pest_conflict_risk=0.1,
        provenance=run_provenance(),
    )
    assert assessment.suitability_score == 35
    with pytest.raises(ValidationError, match="may not exceed 40"):
        IntercropAssessment(**{**assessment.model_dump(), "intercrop_assessment_id": uuid4(), "suitability_score": 70})


def test_rehabilitation_plan_cost_and_budget_invariants():
    cost = CostEstimate(materials_php=1000, labor_php=500, other_php=0, total_php=1500)
    action = RehabilitationAction(
        action_type=RehabilitationActionType.DRAINAGE_IMPROVEMENT,
        timing=RehabilitationTiming.POST_CONFIRMATION,
        problem_detected="Persistent waterlogging",
        likely_cause="Blocked drainage",
        instructions=["Inspect drainage", "Clear confirmed obstruction"],
        cost=cost,
    )
    plan = RehabilitationPlan(
        farm_id=uuid4(), analysis_run_id=uuid4(), actions=[action],
        total_budget_php=2000, total_expected_cost_php=1500,
        expected_recovery_summary="Expected soil-water improvement after drainage restoration.",
        provenance=run_provenance(),
    )
    assert plan.total_expected_cost_php == 1500
    with pytest.raises(ValidationError, match="exceeds total_budget_php"):
        RehabilitationPlan(**{**plan.model_dump(), "rehabilitation_plan_id": uuid4(), "total_budget_php": 1000})


def test_unit_registry_conversions_are_explicit():
    assert convert_value(1, UnitCode.TONNE, UnitCode.KILOGRAM) == 1000
    assert convert_value(10_000, UnitCode.SQUARE_METER, UnitCode.HECTARE) == 1
    assert convert_value(36, UnitCode.KILOMETER_PER_HOUR, UnitCode.METER_PER_SECOND) == pytest.approx(10)
    with pytest.raises(ValueError, match="No supported conversion"):
        convert_value(1, UnitCode.CELSIUS, UnitCode.TONNE)


def test_contract_registry_is_complete_and_schema_digests_are_stable():
    required = {
        "FarmProfile", "FarmCell", "TreeCohort", "FarmObservation", "ProductionRecord",
        "WeatherModelRun", "ProductionForecast", "BayesianPosterior", "PestAssessment",
        "IntercropAssessment", "RehabilitationPlan", "AnalysisRun",
    }
    assert required.issubset(set(contract_registry.names()))
    first = contract_registry.entry("FarmProfile")
    second = contract_registry.entry("FarmProfile")
    assert first.schema_sha256 == second.schema_sha256
    assert len(first.schema_sha256) == 64
