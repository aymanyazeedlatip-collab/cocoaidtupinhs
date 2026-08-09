from __future__ import annotations

from app.domain.enums import ConfidenceLevel
from app.parameters.registry import parameter_registry

INTERCROP_ENGINE_VERSION = "1.0.0"
INTERCROP_PARAMETER_SET_ID = "intercrop-suitability"
INTERCROP_PARAMETER_VERSION = "intercrop-suitability-parameters-1.0.0"
INTERCROP_REQUIREMENT_PROFILE_VERSION = "intercrop-requirements-1.0.0"
CANOPY_LIGHT_ADAPTER_VERSION = "canopy-light-adapter-1.0.0"

PARAMETERS = {
    "component_weights": {
        "light": 0.24,
        "temperature": 0.12,
        "rainfall_water": 0.14,
        "soil_ph": 0.10,
        "drainage": 0.08,
        "space": 0.10,
        "nitrogen": 0.06,
        "management": 0.08,
        "slope": 0.08,
    },
    "competition_penalty_weight": 0.35,
    "pest_penalty_weight": 0.35,
    "hard_constraint_score_cap": 40.0,
    "hard_light_lower_ratio": 0.75,
    "hard_light_upper_ratio": 1.35,
    "hard_slope_degrees": 35.0,
    "canopy_density_reference": 0.65,
    "canopy_density_adjustment_strength": 0.45,
    "canopy_density_factor_min": 0.50,
    "canopy_density_factor_max": 1.25,
    "orientation_adjustment_amplitude": 0.05,
    "economic_suitability_floor": 0.20,
    "high_score_threshold": 70.0,
    "very_high_score_threshold": 85.0,
}

parameter_registry.register(
    parameter_set_id=INTERCROP_PARAMETER_SET_ID,
    version=INTERCROP_PARAMETER_VERSION,
    domain="Spatial intercropping suitability, canopy light, competition, pest conflict, and economic scaling",
    status="experimental_phase_7",
    values=PARAMETERS,
    confidence=ConfidenceLevel.LOW,
    limitations=[
        "PCA brochure directly supports crop light bands and canopy light-transmission table values.",
        "Non-light candidate requirements and scoring constants are development assumptions pending expert validation.",
        "Economic profiles represent historical gross revenue, not net profit or guaranteed future income.",
    ],
)
