from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.enums import EvidenceStatus
from app.domain.intercropping import IntercropAssessmentRequest
from app.domain.pest import PestObservation
from app.domain.rehabilitation import RehabilitationCellContext, RehabilitationPlanRequest
from app.domain.units import UnitCode
from app.engines.intercropping import IntercroppingEngine
from app.engines.pest_inference import PestInferenceEngine
from app.pest import repository as pest_repository
from tests.phase6_factory import pest_context, pest_request
from tests.phase7_factory import cell_context, prepare_phase7_production


def prepare_phase8_dependencies(*, confirmed_pest: bool = True, database_path=None):
    production = prepare_phase7_production(database_path=database_path)
    cell_id = uuid4()
    observation_ids = []
    if confirmed_pest:
        observation = PestObservation(
            farm_id=production.forecast.farm_id,
            cell_id=cell_id,
            production_forecast_id=production.forecast.production_forecast_id,
            pest_profile_id="coconut-scale-insect",
            factor_code="scale_colonies",
            evidence_status=EvidenceStatus.FIELD_CONFIRMED,
            observed_at=datetime(2026, 8, 3, 7, tzinfo=UTC),
            value=True,
            unit=UnitCode.FRACTION,
            prevalence_fraction=0.12,
            source_label="Phase 8 test inspection",
        )
        observation_id, _ = pest_repository.save_observation(observation, database_path=database_path)
        observation_ids = [observation_id]
    pest = PestInferenceEngine(database_path=database_path).execute(pest_request(
        production,
        cell_id=cell_id,
        pest_profile_ids=["coconut-scale-insect"],
        observation_ids=observation_ids,
        context=pest_context(
            total_palms=425, young_palms=25, healthy_bearing_palms=270,
            aging_palms=60, stressed_palms=25, infested_or_diseased_palms=25,
            rehabilitating_palms=10, dead_palms=10,
            symptom_codes=["scale_colonies_on_leaflets"] if confirmed_pest else [],
        ),
    )).output
    intercrop = IntercroppingEngine(database_path=database_path).execute(
        IntercropAssessmentRequest(
            farm_id=production.forecast.farm_id,
            production_forecast_id=production.forecast.production_forecast_id,
            pest_assessment_run_id=pest.run_id,
            assessed_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
            candidate_ids=["cacao", "coffee", "banana"],
            cells=[cell_context(cell_id=cell_id, label="Phase 8 Cell")],
            farm_data_version="phase8-test-farm-1",
        )
    ).output
    return production, pest, intercrop, cell_id


def rehabilitation_cell(cell_id, **updates) -> RehabilitationCellContext:
    payload = {
        "cell_id": cell_id,
        "label": "Phase 8 Cell",
        "area_hectares": 1.0,
        "total_palms": 425,
        "young_palms": 25,
        "healthy_bearing_palms": 270,
        "aging_palms": 60,
        "stressed_palms": 25,
        "infested_or_diseased_palms": 25,
        "rehabilitating_palms": 10,
        "dead_palms": 10,
        "drainage_index": 0.35,
        "soil_fertility_index": 0.40,
        "soil_water_index": 0.55,
        "production_decline_fraction": 0.18,
        "nutrient_deficiency_status": "field_confirmed",
        "storm_damage_status": None,
        "sanitation_quality": 0.45,
        "access_feasibility": 0.75,
    }
    payload.update(updates)
    return RehabilitationCellContext.model_validate(payload)


def rehabilitation_request(production, pest, intercrop, cell_id, **updates) -> RehabilitationPlanRequest:
    payload = {
        "farm_id": production.forecast.farm_id,
        "production_forecast_id": production.forecast.production_forecast_id,
        "posterior_id": None,
        "pest_assessment_run_id": pest.run_id,
        "intercropping_run_id": intercrop.run_id,
        "planned_at": datetime(2026, 8, 4, 8, tzinfo=UTC),
        "cells": [rehabilitation_cell(cell_id)],
        "total_budget_php": 150000,
        "available_labor_person_days": 100,
        "planning_horizon_months": 24,
        "annual_discount_rate": 0.08,
        "risk_aversion": 0.35,
        "farm_data_version": "phase8-test-farm-1",
    }
    payload.update(updates)
    return RehabilitationPlanRequest.model_validate(payload)
