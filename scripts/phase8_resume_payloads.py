from __future__ import annotations

from datetime import datetime

DEFAULT_CELL_ID = "11111111-1111-4111-8111-111111111111"


def pest_assessment_payload(
    *,
    farm_id: str,
    production_forecast_id: str,
    observation_id: str | None = None,
    assessed_at: datetime,
    cell_id: str = DEFAULT_CELL_ID,
) -> dict:
    return {
        "farm_id": farm_id,
        "cell_id": cell_id,
        "production_forecast_id": production_forecast_id,
        "posterior_id": None,
        "pest_profile_ids": [
            "bud-nut-rot",
            "coconut-leaf-beetle",
            "rhinoceros-beetle",
            "asiatic-palm-weevil",
            "coconut-scale-insect",
        ],
        "assessed_at": assessed_at.isoformat(),
        "context": {
            "total_palms": 425,
            "young_palms": 25,
            "healthy_bearing_palms": 270,
            "aging_palms": 60,
            "stressed_palms": 25,
            "infested_or_diseased_palms": 25,
            "rehabilitating_palms": 10,
            "dead_palms": 10,
            "mean_palm_age_years": 18,
            "maintenance_quality": 0.45,
            "sanitation_quality": 0.45,
            "drainage_quality": 0.35,
            "waterlogging": False,
            "natural_enemies_present": False,
            "decaying_organic_breeding_material": False,
            "fresh_palm_wounds": False,
            "storm_damage": False,
            "symptom_codes": ["scale_colonies_on_leaflets"],
        },
        "observation_ids": [observation_id] if observation_id else [],
        "nearby_confirmed_cases": [],
        "farm_data_version": "phase8-manual-test-farm-1",
    }


def intercropping_payload(
    *,
    farm_id: str,
    production_forecast_id: str,
    pest_assessment_run_id: str,
    assessed_at: datetime,
    cell_id: str = DEFAULT_CELL_ID,
) -> dict:
    return {
        "farm_id": farm_id,
        "production_forecast_id": production_forecast_id,
        "posterior_id": None,
        "pest_assessment_run_id": pest_assessment_run_id,
        "assessed_at": assessed_at.isoformat(),
        "candidate_ids": ["cacao", "coffee", "banana", "sugarcane"],
        "cells": [
            {
                "cell_id": cell_id,
                "label": "Manual Test Cell A",
                "area_hectares": 1,
                "palm_age_years": 40,
                "spacing_x_m": 8,
                "spacing_y_m": 8,
                "canopy_design": "square",
                "canopy_density_index": 0.65,
                "row_orientation_degrees": None,
                "slope_degrees": 4,
                "drainage_index": 0.65,
                "soil_ph": 6.1,
                "soil_moisture_index": 0.58,
                "nitrogen_index": 0.65,
                "available_space_fraction": 0.7,
                "management_feasibility": 0.72,
                "market_access_index": 0.6,
            }
        ],
        "farm_data_version": "phase8-manual-test-farm-1",
        "include_economic_potential": True,
    }


def rehabilitation_payload(
    *,
    farm_id: str,
    production_forecast_id: str,
    pest_assessment_run_id: str,
    intercropping_run_id: str,
    planned_at: datetime,
    cell_id: str = DEFAULT_CELL_ID,
) -> dict:
    return {
        "farm_id": farm_id,
        "production_forecast_id": production_forecast_id,
        "posterior_id": None,
        "pest_assessment_run_id": pest_assessment_run_id,
        "intercropping_run_id": intercropping_run_id,
        "planned_at": planned_at.isoformat(),
        "cells": [
            {
                "cell_id": cell_id,
                "label": "Manual Test Cell A",
                "area_hectares": 1,
                "total_palms": 425,
                "young_palms": 25,
                "healthy_bearing_palms": 270,
                "aging_palms": 60,
                "stressed_palms": 25,
                "infested_or_diseased_palms": 25,
                "rehabilitating_palms": 10,
                "dead_palms": 10,
                "drainage_index": 0.35,
                "soil_fertility_index": 0.4,
                "soil_water_index": 0.55,
                "production_decline_fraction": 0.18,
                "nutrient_deficiency_status": "field_confirmed",
                "storm_damage_status": None,
                "sanitation_quality": 0.45,
                "access_feasibility": 0.75,
            }
        ],
        "total_budget_php": 150000,
        "available_labor_person_days": 100,
        "planning_horizon_months": 24,
        "annual_discount_rate": 0.08,
        "risk_aversion": 0.35,
        "farm_data_version": "phase8-manual-test-farm-1",
    }
