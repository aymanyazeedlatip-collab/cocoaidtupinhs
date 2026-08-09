from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.bayesian import (
    BayesianEvidenceObservation,
    BayesianSimulationRequest,
)
from app.domain.units import UnitCode
from tests.phase5_factory import initial_state


def test_bayesian_evidence_contract_enforces_type_specific_units_and_statuses():
    observation = BayesianEvidenceObservation(
        farm_id=uuid4(),
        evidence_type="pest_prevalence",
        evidence_status="field_confirmed",
        observed_at=datetime.now(UTC),
        value=15,
        unit=UnitCode.PERCENT,
    )
    assert observation.value == 15
    with pytest.raises(ValidationError, match="requires one of"):
        BayesianEvidenceObservation(
            farm_id=uuid4(),
            evidence_type="actual_rainfall",
            evidence_status="field_confirmed",
            observed_at=datetime.now(UTC),
            value=20,
            unit=UnitCode.COUNT,
        )
    with pytest.raises(ValidationError, match="exceeds"):
        BayesianEvidenceObservation(
            farm_id=uuid4(),
            evidence_type="storm_damage",
            evidence_status="expert_confirmed",
            observed_at=datetime.now(UTC),
            value=1.2,
            unit=UnitCode.FRACTION,
        )


def test_bayesian_request_requires_exactly_one_state_source_and_unique_evidence():
    forecast_id = uuid4()
    now = datetime.now(UTC)
    request = BayesianSimulationRequest(
        production_forecast_id=forecast_id,
        initial_state=initial_state(),
        baseline_state_date=now,
    )
    assert request.particle_count == 1000
    with pytest.raises(ValidationError, match="exactly one"):
        BayesianSimulationRequest(
            production_forecast_id=forecast_id,
            baseline_state_date=now,
        )
    with pytest.raises(ValidationError, match="duplicates"):
        observation_id = uuid4()
        BayesianSimulationRequest(
            production_forecast_id=forecast_id,
            initial_state=initial_state(),
            baseline_state_date=now,
            evidence_observation_ids=[observation_id, observation_id],
        )
