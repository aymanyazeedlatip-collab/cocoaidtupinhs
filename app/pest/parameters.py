from __future__ import annotations

import math
from typing import Any

from app.domain.enums import ConfidenceLevel
from app.parameters.registry import parameter_registry

PEST_PARAMETER_VERSION = "pest-inference-parameters-1.0.0"
PEST_PARAMETER_SET_ID = "v3.pest_inference"
SUPPORTED_PEST_IDS = (
    "bud-nut-rot",
    "coconut-leaf-beetle",
    "rhinoceros-beetle",
    "asiatic-palm-weevil",
    "coconut-scale-insect",
)

# These are transparent development parameters, not prevalence estimates. The PCA
# references provide qualitative rules but not calibrated likelihood ratios.
PARAMETERS: dict[str, Any] = {
    "baseline_inspection_prior": 0.05,
    "evidence_reliability": {
        "predicted": 0.0,
        "suspected": 0.0,
        "farmer_reported": 0.45,
        "field_confirmed": 0.85,
        "expert_confirmed": 1.0,
    },
    "likelihood_ratios": {
        "increases_risk": {"low": 1.30, "moderate": 1.80, "high": 2.60},
        "decreases_risk": {"low": 0.85, "moderate": 0.65, "high": 0.45},
        "diagnostic_signal": {"low": 2.50, "moderate": 5.00, "high": 9.00},
    },
    "spatial": {
        "half_distance_m": 2000.0,
        "maximum_likelihood_ratio": 3.0,
        "farmer_reported_weight": 0.45,
        "field_confirmed_weight": 0.85,
        "expert_confirmed_weight": 1.0,
    },
    "severity": {
        "minimum": 0.10,
        "maximum": 0.85,
        "diagnostic_increment": 0.18,
        "vulnerability_weight": 0.45,
        "current_infestation_weight": 0.35,
    },
    "observation_prevalence_max_likelihood_ratio": 6.0,
    "inspection_days": {"critical": 0, "high": 1, "moderate": 3, "low": 14},
    "risk_thresholds": {"moderate": 0.20, "high": 0.45, "critical": 0.70},
}


def likelihood_ratio(direction: str, confidence: str) -> float:
    return float(PARAMETERS["likelihood_ratios"][direction][confidence])


def evidence_reliability(status: str) -> float:
    return float(PARAMETERS["evidence_reliability"][status])


def spatial_kernel(distance_m: float) -> float:
    half_distance = float(PARAMETERS["spatial"]["half_distance_m"])
    return math.exp(-math.log(2.0) * max(0.0, float(distance_m)) / half_distance)


parameter_registry.register(
    parameter_set_id=PEST_PARAMETER_SET_ID,
    version=PEST_PARAMETER_VERSION,
    domain="PCA pest-specific evidence inference, spatial pressure, and loss separation",
    status="experimental_phase_6",
    values=PARAMETERS,
    confidence=ConfidenceLevel.LOW,
    limitations=[
        "PCA references provide qualitative evidence rules but not calibrated likelihood ratios or farm prevalence priors.",
        "Likelihood ratios, spatial decay, and severity coefficients are transparent development assumptions pending expert and field calibration.",
        "The engine produces inspection priority and probabilistic decision support, not laboratory diagnosis.",
    ],
)
