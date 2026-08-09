from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.intercropping import IntercropAssessmentRequest, IntercropCellContext
from app.engines.pest_inference import PestInferenceEngine
from tests.phase6_factory import pest_context, pest_request, prepare_phase6_production


def prepare_phase7_production(*, farm_id=None, database_path=None):
    return prepare_phase6_production(farm_id=farm_id, database_path=database_path)


def cell_context(**updates) -> IntercropCellContext:
    payload = {
        "cell_id": uuid4(),
        "label": "Cell A",
        "area_hectares": 1.0,
        "palm_age_years": 40,
        "spacing_x_m": 8.0,
        "spacing_y_m": 8.0,
        "canopy_design": "square",
        "canopy_density_index": 0.65,
        "row_orientation_degrees": None,
        "slope_degrees": 4.0,
        "drainage_index": 0.65,
        "soil_ph": 6.1,
        "soil_moisture_index": 0.58,
        "nitrogen_index": 0.65,
        "available_space_fraction": 0.70,
        "management_feasibility": 0.72,
        "market_access_index": 0.60,
    }
    payload.update(updates)
    return IntercropCellContext.model_validate(payload)


def intercropping_request(production, **updates) -> IntercropAssessmentRequest:
    payload = {
        "farm_id": production.forecast.farm_id,
        "production_forecast_id": production.forecast.production_forecast_id,
        "posterior_id": None,
        "pest_assessment_run_id": None,
        "assessed_at": datetime(2026, 8, 3, 8, tzinfo=UTC),
        "candidate_ids": ["cacao", "coffee", "banana", "sugarcane"],
        "cells": [cell_context()],
        "farm_data_version": "phase7-test-farm-1",
        "include_economic_potential": True,
    }
    payload.update(updates)
    return IntercropAssessmentRequest.model_validate(payload)


def prepare_high_bud_rot_pest_run(production, *, database_path=None):
    request = pest_request(
        production,
        pest_profile_ids=["bud-nut-rot"],
        context=pest_context(
            waterlogging=True,
            drainage_quality=0.20,
            maintenance_quality=0.35,
            symptom_codes=["bud_rot_symptoms"],
        ),
    )
    return PestInferenceEngine(database_path=database_path).execute(request).output
