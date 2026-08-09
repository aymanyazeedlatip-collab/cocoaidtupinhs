from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.decision_support import DecisionSupportRequest


def test_phase9_request_requires_production_and_unique_components():
    base = {
        "farm_id": uuid4(),
        "production_forecast_id": uuid4(),
        "generated_at": datetime(2026, 8, 4, tzinfo=UTC),
        "farm_data_version": "test",
    }
    with pytest.raises(ValueError):
        DecisionSupportRequest.model_validate({**base, "requested_components": ["pest"]})
    with pytest.raises(ValueError):
        DecisionSupportRequest.model_validate({**base, "requested_components": ["production", "production"]})


def test_phase9_request_rejects_naive_datetime():
    with pytest.raises(ValueError):
        DecisionSupportRequest(
            farm_id=uuid4(), production_forecast_id=uuid4(),
            generated_at=datetime(2026, 8, 4), farm_data_version="test",
        )
