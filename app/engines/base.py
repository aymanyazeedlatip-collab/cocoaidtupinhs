from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.errors import EngineExecutionError
from app.domain.base import StrictModel
from app.domain.enums import EngineAvailability, EngineMaturity

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class EngineDescriptor(StrictModel):
    engine_id: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=240)
    version: str = Field(min_length=1, max_length=120)
    maturity: EngineMaturity
    availability: EngineAvailability
    input_contract: str = Field(min_length=1, max_length=160)
    output_contract: str = Field(min_length=1, max_length=160)
    deterministic_with_seed: bool = False
    dependencies: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)


class EngineExecutionContext(StrictModel):
    execution_id: UUID = Field(default_factory=uuid4)
    analysis_run_id: UUID | None = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    random_seed: int | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class EngineExecutionResult(StrictModel, Generic[OutputT]):
    execution_id: UUID
    engine_id: str
    engine_version: str
    started_at: datetime
    completed_at: datetime
    duration_ms: float = Field(ge=0)
    output: OutputT
    warnings: list[str] = Field(default_factory=list)


class AnalyticalEngine(ABC, Generic[InputT, OutputT]):
    """Common boundary for analytical engines.

    Subclasses declare strict Pydantic input/output contracts and implement only
    `_run`. Validation, timing, metadata, and safe exception translation are shared.
    """

    descriptor: EngineDescriptor
    input_model: type[InputT]
    output_model: type[OutputT]

    def validate_input(self, payload: InputT | dict[str, Any]) -> InputT:
        return payload if isinstance(payload, self.input_model) else self.input_model.model_validate(payload)

    def validate_output(self, payload: OutputT | dict[str, Any]) -> OutputT:
        return payload if isinstance(payload, self.output_model) else self.output_model.model_validate(payload)

    def execute(
        self,
        payload: InputT | dict[str, Any],
        context: EngineExecutionContext | None = None,
    ) -> EngineExecutionResult[OutputT]:
        if self.descriptor.availability != EngineAvailability.AVAILABLE:
            raise EngineExecutionError(
                f"Engine {self.descriptor.engine_id} is not executable",
                details={"availability": self.descriptor.availability},
            )
        execution_context = context or EngineExecutionContext()
        validated_input = self.validate_input(payload)
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        try:
            output, warnings = self._run(validated_input, execution_context)
            validated_output = self.validate_output(output)
        except EngineExecutionError:
            raise
        except Exception as exc:
            raise EngineExecutionError(
                f"Engine {self.descriptor.engine_id} failed",
                details={"exception_type": type(exc).__name__},
            ) from exc
        completed_at = datetime.now(UTC)
        return EngineExecutionResult[OutputT](
            execution_id=execution_context.execution_id,
            engine_id=self.descriptor.engine_id,
            engine_version=self.descriptor.version,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=(time.perf_counter() - started) * 1000,
            output=validated_output,
            warnings=warnings,
        )

    @abstractmethod
    def _run(self, payload: InputT, context: EngineExecutionContext) -> tuple[OutputT | dict[str, Any], list[str]]:
        raise NotImplementedError

    def explain_result(self, result: OutputT) -> dict[str, Any]:
        """Return a structured explanation suitable for a future narrative layer."""
        return {
            "engine_id": self.descriptor.engine_id,
            "engine_version": self.descriptor.version,
            "output_contract": self.descriptor.output_contract,
            "summary": result.model_dump(mode="json"),
        }
