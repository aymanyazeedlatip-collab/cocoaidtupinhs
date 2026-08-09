from __future__ import annotations

from pydantic import Field
import pytest

from app.core.errors import EngineExecutionError, EngineNotFoundError
from app.domain.base import StrictModel
from app.domain.enums import EngineAvailability, EngineMaturity
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.engines.registry import EngineRegistry, engine_registry


class AddInput(StrictModel):
    left: float
    right: float


class AddOutput(StrictModel):
    total: float


class AddEngine(AnalyticalEngine[AddInput, AddOutput]):
    descriptor = EngineDescriptor(
        engine_id="test.add",
        name="Test Add Engine",
        version="1.0.0",
        maturity=EngineMaturity.EXPERIMENTAL,
        availability=EngineAvailability.AVAILABLE,
        input_contract="AddInput",
        output_contract="AddOutput",
        deterministic_with_seed=True,
    )
    input_model = AddInput
    output_model = AddOutput

    def _run(self, payload: AddInput, context: EngineExecutionContext):
        return AddOutput(total=payload.left + payload.right), []


class BrokenEngine(AddEngine):
    descriptor = AddEngine.descriptor.model_copy(update={"engine_id": "test.broken"})

    def _run(self, payload: AddInput, context: EngineExecutionContext):
        raise RuntimeError("internal details must be wrapped")


def test_engine_interface_validates_times_and_wraps_output():
    result = AddEngine().execute({"left": 2, "right": 3}, EngineExecutionContext(random_seed=42))
    assert result.output.total == 5
    assert result.duration_ms >= 0
    assert result.engine_id == "test.add"
    assert AddEngine().explain_result(result.output)["summary"]["total"] == 5


def test_engine_interface_rejects_unknown_input_and_wraps_failures():
    with pytest.raises(Exception):
        AddEngine().execute({"left": 2, "right": 3, "unknown": True})
    with pytest.raises(EngineExecutionError) as exc:
        BrokenEngine().execute({"left": 2, "right": 3})
    assert exc.value.details["exception_type"] == "RuntimeError"


def test_engine_registry_supports_descriptors_before_implementations():
    registry = EngineRegistry()
    registry.register(AddEngine())
    assert registry.engine("test.add").descriptor.version == "1.0.0"
    assert registry.execute("test.add", {"left": 1, "right": 4}).output.total == 5

    planned = EngineDescriptor(
        engine_id="test.planned",
        name="Planned",
        version="0.1.0",
        maturity=EngineMaturity.CONTRACT_ONLY,
        availability=EngineAvailability.PLANNED,
        input_contract="AddInput",
        output_contract="AddOutput",
    )
    registry.register_descriptor(planned)
    with pytest.raises(EngineNotFoundError, match="no executable implementation"):
        registry.engine("test.planned")


def test_global_engine_catalog_contains_dependency_order_modules():
    ids = {item.engine_id for item in engine_registry.descriptors()}
    assert {
        "legacy.production", "legacy.bayesian", "v3.weather_assimilation", "v3.production",
        "v3.bayesian", "v3.pest_inference", "v3.intercropping", "v3.rehabilitation",
    }.issubset(ids)
    assert engine_registry.descriptor("v3.rehabilitation").availability == EngineAvailability.AVAILABLE
