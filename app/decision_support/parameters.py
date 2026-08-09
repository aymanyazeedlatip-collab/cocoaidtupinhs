from app.domain.enums import ConfidenceLevel
from app.parameters.registry import parameter_registry

DECISION_SUPPORT_ENGINE_VERSION = "1.0.0"
DECISION_SUPPORT_PARAMETER_SET_ID = "integrated-decision-support-network"
DECISION_SUPPORT_PARAMETER_VERSION = "decision-support-parameters-1.0.0"
DEPENDENCY_GRAPH_VERSION = "decision-support-dependency-graph-1.0.0"

DEPENDENCY_GRAPH = {
    "production": [],
    "bayesian": ["production"],
    "pest": ["production"],
    "intercropping": ["production"],
    "rehabilitation": ["production"],
}

PARAMETERS = {
    "dependency_graph_version": DEPENDENCY_GRAPH_VERSION,
    "dependency_graph": DEPENDENCY_GRAPH,
    "priority_thresholds": {
        "critical_decline_probability": 0.75,
        "high_decline_probability": 0.50,
        "critical_mortality_probability": 0.50,
        "high_mortality_probability": 0.30,
        "critical_pest_probability": 0.80,
        "high_pest_probability": 0.60,
        "moderate_pest_probability": 0.35,
        "moderate_intercrop_score": 70.0,
    },
    "failure_policies": ["continue_optional", "strict"],
    "source_output_mutation": False,
}

PRIORITY_ORDER = {"routine": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}

parameter_registry.register(
    parameter_set_id=DECISION_SUPPORT_PARAMETER_SET_ID,
    version=DECISION_SUPPORT_PARAMETER_VERSION,
    domain="Integrated analytical dependency resolution, recommendation prioritization, and traceability",
    status="experimental_phase_9",
    values=PARAMETERS,
    confidence=ConfidenceLevel.MODERATE,
    limitations=[
        "The network interprets stored analytical outputs and does not create new field evidence.",
        "Priority thresholds are transparent development rules pending expert and field validation.",
        "Recommendations do not replace PCA diagnosis, local cost verification, or farmer consent.",
    ],
)
