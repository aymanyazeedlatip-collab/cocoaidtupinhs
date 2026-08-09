from __future__ import annotations

from threading import RLock
from typing import Any

from app.core.errors import EngineNotFoundError
from app.engines.base import AnalyticalEngine, EngineDescriptor


class EngineRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, EngineDescriptor] = {}
        self._engines: dict[str, AnalyticalEngine] = {}
        self._lock = RLock()

    def register_descriptor(self, descriptor: EngineDescriptor) -> None:
        with self._lock:
            existing = self._descriptors.get(descriptor.engine_id)
            if existing is not None and existing != descriptor:
                raise ValueError(f"Engine descriptor already registered: {descriptor.engine_id}")
            self._descriptors[descriptor.engine_id] = descriptor

    def register(self, engine: AnalyticalEngine) -> None:
        with self._lock:
            self.register_descriptor(engine.descriptor)
            existing = self._engines.get(engine.descriptor.engine_id)
            if existing is not None and existing is not engine:
                raise ValueError(f"Engine already registered: {engine.descriptor.engine_id}")
            self._engines[engine.descriptor.engine_id] = engine

    def descriptors(self) -> list[EngineDescriptor]:
        with self._lock:
            return [self._descriptors[key] for key in sorted(self._descriptors)]

    def descriptor(self, engine_id: str) -> EngineDescriptor:
        with self._lock:
            descriptor = self._descriptors.get(engine_id)
        if descriptor is None:
            raise EngineNotFoundError(
                f"Unknown analytical engine: {engine_id}",
                details={"available": [item.engine_id for item in self.descriptors()]},
            )
        return descriptor

    def engine(self, engine_id: str) -> AnalyticalEngine:
        with self._lock:
            engine = self._engines.get(engine_id)
        if engine is None:
            descriptor = self.descriptor(engine_id)
            raise EngineNotFoundError(
                f"Engine {engine_id} has no executable implementation in this phase",
                details={"availability": descriptor.availability, "maturity": descriptor.maturity},
            )
        return engine

    def execute(self, engine_id: str, payload: dict[str, Any]):
        return self.engine(engine_id).execute(payload)


engine_registry = EngineRegistry()
