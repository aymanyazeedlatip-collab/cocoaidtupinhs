from __future__ import annotations

from app.domain.enums import EngineAvailability, EngineMaturity
from app.engines.base import EngineDescriptor
from app.engines.registry import engine_registry
from app.engines.weather_assimilation import WEATHER_ASSIMILATION_DESCRIPTOR
from app.engines.production import PRODUCTION_DESCRIPTOR
from app.engines.bayesian import BAYESIAN_DESCRIPTOR
from app.engines.pest_inference import PEST_DESCRIPTOR
from app.engines.intercropping import INTERCROP_DESCRIPTOR
from app.engines.rehabilitation import REHABILITATION_DESCRIPTOR
from app.engines.decision_support import DECISION_SUPPORT_DESCRIPTOR


DESCRIPTORS = [
    EngineDescriptor(
        engine_id="legacy.production",
        name="Legacy Production Model",
        version="production-synthetic-1.0",
        maturity=EngineMaturity.LEGACY,
        availability=EngineAvailability.AVAILABLE,
        input_contract="legacy.FarmCreate",
        output_contract="legacy.production_prediction",
        limitations=["Synthetic/reference-based training data", "Legacy feature contract"],
    ),
    EngineDescriptor(
        engine_id="legacy.bayesian",
        name="Legacy Farm Simulation",
        version="coco-aid-math-2.4.1",
        maturity=EngineMaturity.LEGACY,
        availability=EngineAvailability.AVAILABLE,
        input_contract="legacy.SimulationRequest",
        output_contract="legacy.simulation_result",
        deterministic_with_seed=True,
        limitations=["Not yet observation-aware", "Retained only for shadow comparison"],
    ),
    EngineDescriptor(
        engine_id="legacy.pest",
        name="Legacy Pest Risk Model",
        version="pest-synthetic-1.0",
        maturity=EngineMaturity.LEGACY,
        availability=EngineAvailability.AVAILABLE,
        input_contract="legacy.PestRiskRequest",
        output_contract="legacy.pest_result",
        limitations=["Synthetic/reference-based training data"],
    ),
    WEATHER_ASSIMILATION_DESCRIPTOR,
    PRODUCTION_DESCRIPTOR,
    BAYESIAN_DESCRIPTOR,
    PEST_DESCRIPTOR,
    INTERCROP_DESCRIPTOR,
    REHABILITATION_DESCRIPTOR,
    DECISION_SUPPORT_DESCRIPTOR,
]


def register_catalog() -> None:
    for descriptor in DESCRIPTORS:
        engine_registry.register_descriptor(descriptor)


register_catalog()
