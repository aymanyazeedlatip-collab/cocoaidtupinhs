from __future__ import annotations

import hashlib
import json
from threading import RLock
from typing import Any

from pydantic import Field

from app.domain.base import StrictModel
from app.domain.enums import ConfidenceLevel
from app.domain.provenance import SourceReference


class ParameterSetDescriptor(StrictModel):
    parameter_set_id: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=120)
    domain: str = Field(min_length=1, max_length=120)
    status: str = Field(min_length=1, max_length=80)
    values_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameter_count: int = Field(ge=0)
    confidence: ConfidenceLevel
    source_references: list[SourceReference] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ParameterRegistry:
    def __init__(self) -> None:
        self._sets: dict[str, tuple[ParameterSetDescriptor, dict[str, Any]]] = {}
        self._lock = RLock()

    def register(
        self,
        *,
        parameter_set_id: str,
        version: str,
        domain: str,
        status: str,
        values: dict[str, Any],
        confidence: ConfidenceLevel,
        source_references: list[SourceReference] | None = None,
        limitations: list[str] | None = None,
    ) -> ParameterSetDescriptor:
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        descriptor = ParameterSetDescriptor(
            parameter_set_id=parameter_set_id,
            version=version,
            domain=domain,
            status=status,
            values_sha256=hashlib.sha256(encoded).hexdigest(),
            parameter_count=len(values),
            confidence=confidence,
            source_references=source_references or [],
            limitations=limitations or [],
        )
        key = f"{parameter_set_id}@{version}"
        with self._lock:
            existing = self._sets.get(key)
            if existing is not None and existing[0] != descriptor:
                raise ValueError(f"Parameter set already registered with different content: {key}")
            self._sets[key] = (descriptor, dict(values))
        return descriptor

    def descriptors(self) -> list[ParameterSetDescriptor]:
        with self._lock:
            return [self._sets[key][0] for key in sorted(self._sets)]

    def values(self, parameter_set_id: str, version: str) -> dict[str, Any]:
        key = f"{parameter_set_id}@{version}"
        with self._lock:
            item = self._sets.get(key)
        if item is None:
            raise KeyError(key)
        return dict(item[1])


parameter_registry = ParameterRegistry()
parameter_registry.register(
    parameter_set_id="legacy.core",
    version="psa-calibrated-parameters-2.4.1",
    domain="legacy simulation and assessment",
    status="frozen_legacy",
    values={"calculation_version": "coco-aid-math-2.4.1"},
    confidence=ConfidenceLevel.LOW,
    limitations=[
        "Legacy parameters are retained for compatibility and shadow comparison.",
        "Field calibration and parameter-level PCA provenance remain Phase 2 work.",
    ],
)
parameter_registry.register(
    parameter_set_id="v3.contracts",
    version="3.0.0-draft.2",
    domain="units, validation limits, and data-contract semantics",
    status="phase_2_active",
    values={
        "max_live_forecast_days": 16,
        "probability_scale": "0_to_1",
        "suitability_score_scale": "0_to_100",
        "area_unit": "ha",
        "production_mass_unit": "t",
        "rainfall_unit": "mm",
        "temperature_unit": "degC",
    },
    confidence=ConfidenceLevel.HIGH,
)

parameter_registry.register(
    parameter_set_id="v3.bayesian_farm_state",
    version="bayesian-farm-state-parameters-1.0.0",
    domain="Bayesian palm-state transitions and observation likelihoods",
    status="experimental_phase_5",
    values={
        "default_particle_count": 1000,
        "maximum_particle_count": 5000,
        "evidence_reliability": {
            "predicted": 0.0,
            "suspected": 0.0,
            "farmer_reported": 0.35,
            "field_confirmed": 0.75,
            "expert_confirmed": 1.0,
        },
        "prior_weather_sensitivity": {"alpha": 3.5, "beta": 6.5},
        "prior_pest_sensitivity": {"alpha": 3.0, "beta": 7.0},
        "prior_annual_mortality_rate": {"alpha": 1.5, "beta": 98.5},
        "prior_rehabilitation_success": {"alpha": 7.0, "beta": 3.0},
        "prior_soil_recovery_rate": {"alpha": 5.0, "beta": 5.0},
        "prior_pest_loss_fraction": {"alpha": 2.0, "beta": 8.0},
        "resampling_ess_fraction": 0.75,
    },
    confidence=ConfidenceLevel.LOW,
    limitations=[
        "Development priors and monthly transitions require longitudinal farm calibration.",
        "Evidence likelihood widths are transparent assumptions pending expert validation.",
    ],
)
