from __future__ import annotations

from app.domain.enums import ConfidenceLevel
from app.parameters.registry import parameter_registry

REHABILITATION_ENGINE_VERSION = "1.0.0"
REHABILITATION_PARAMETER_SET_ID = "rehabilitation-scenario-optimization"
REHABILITATION_PARAMETER_VERSION = "rehabilitation-scenario-parameters-1.0.0"
REHABILITATION_COST_CATALOG_VERSION = "rehabilitation-cost-catalog-1.0.0"

# These are explicit development assumptions for scenario comparison. They are
# not official PCA prices, prescribed chemical dosages, or guaranteed outcomes.
PARAMETERS = {
    "labor_day_rate_php": 800.0,
    "coconut_value_php_per_tonne": 25000.0,
    "trigger_thresholds": {
        "dead_fraction_partial": 0.05,
        "dead_fraction_complete": 0.30,
        "aging_fraction": 0.35,
        "stressed_fraction": 0.15,
        "infested_fraction": 0.05,
        "low_drainage": 0.40,
        "low_fertility": 0.45,
        "production_decline": 0.10,
        "pest_probability": 0.30,
        "critical_pest_probability": 0.65,
        "intercrop_suitability": 70.0,
    },
    "cost_catalog": {
        "inspect": {"materials_per_ha": 100.0, "labor_days_per_ha": 1.0, "other_per_ha": 0.0, "recovery_days": 7},
        "monitor": {"materials_per_ha": 100.0, "labor_days_per_ha": 0.5, "other_per_ha": 0.0, "recovery_days": 30},
        "sanitation": {"materials_per_ha": 1500.0, "labor_days_per_ha": 2.0, "other_per_ha": 0.0, "recovery_days": 90},
        "remove_breeding_material": {"materials_per_ha": 2500.0, "labor_days_per_ha": 3.0, "other_per_ha": 500.0, "recovery_days": 60},
        "drainage_improvement": {"materials_per_ha": 8000.0, "labor_days_per_ha": 7.5, "other_per_ha": 1000.0, "recovery_days": 120},
        "organic_matter_application": {"materials_per_ha": 6000.0, "labor_days_per_ha": 4.0, "other_per_ha": 500.0, "recovery_days": 180},
        "fertilizer_correction": {"materials_per_ha": 7500.0, "labor_days_per_ha": 3.0, "other_per_ha": 500.0, "recovery_days": 180},
        "pest_or_disease_treatment": {"materials_per_ha": 5000.0, "labor_days_per_ha": 4.0, "other_per_ha": 500.0, "recovery_days": 120},
        "pruning_or_crown_management": {"materials_per_ha": 1200.0, "labor_days_per_ha": 3.0, "other_per_ha": 0.0, "recovery_days": 90},
        "partial_replanting": {"materials_per_ha": 25000.0, "labor_days_per_ha": 12.5, "other_per_ha": 2000.0, "recovery_days": 1095},
        "complete_replanting": {"materials_per_ha": 60000.0, "labor_days_per_ha": 25.0, "other_per_ha": 5000.0, "recovery_days": 1825},
        "variety_replacement": {"materials_per_ha": 70000.0, "labor_days_per_ha": 27.5, "other_per_ha": 5000.0, "recovery_days": 1825},
        "intercropping_adjustment": {"materials_per_ha": 12000.0, "labor_days_per_ha": 8.0, "other_per_ha": 1000.0, "recovery_days": 180},
    },
    "scenario_effects": {
        "no_action": {"recovery": 0.0, "risk_reduction": 0.0},
        "pest_management": {"recovery": 0.08, "risk_reduction": 0.45},
        "fertilization": {"recovery": 0.09, "risk_reduction": 0.15},
        "replanting": {"recovery": 0.05, "risk_reduction": 0.30},
        "intercropping": {"recovery": 0.02, "risk_reduction": 0.08},
        "combined_rehabilitation": {"recovery": 0.16, "risk_reduction": 0.60},
    },
    "uncertainty_fraction": {"lower": 0.85, "upper": 1.15},
    "risk_penalty_loss_fraction": 0.25,
    "inspection_delay_days": 1,
    "action_delay_days": 7,
    "follow_up_days": [30, 90, 180],
}

parameter_registry.register(
    parameter_set_id=REHABILITATION_PARAMETER_SET_ID,
    version=REHABILITATION_PARAMETER_VERSION,
    domain="Evidence-linked rehabilitation actions, cost/labor scenarios, and budget-constrained expected utility",
    status="experimental_phase_8",
    values=PARAMETERS,
    confidence=ConfidenceLevel.LOW,
    limitations=[
        "Cost and labor values are transparent development assumptions and require local validation.",
        "Production recovery effects are scenario assumptions, not causal field estimates.",
        "Predicted hazards and inferred pest risk trigger inspection, not automatic damage confirmation or treatment.",
        "Economic utility uses a development coconut value and gross intercrop revenue where available.",
    ],
)
