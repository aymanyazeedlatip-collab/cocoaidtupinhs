from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.contract_registry import contract_registry
from app.domain.intercropping import IntercropAssessmentRequest, IntercropCellContext
from tests.phase7_factory import cell_context


def test_phase7_contracts_registered_and_versioned():
    names = set(contract_registry.names())
    assert {
        "IntercropAssessmentRequest", "IntercropCellContext", "CanopyLightEstimate",
        "IntercropCandidateAssessment", "IntercropEngineOutput",
    } <= names
    schema = contract_registry.schema("IntercropEngineOutput")
    assert schema["properties"]["schema_version"]["default"] == "3.0.0-draft.10"


def test_request_rejects_duplicate_cell_ids():
    cell_id = uuid4()
    with pytest.raises(ValidationError):
        IntercropAssessmentRequest(
            farm_id=uuid4(), production_forecast_id=uuid4(),
            assessed_at=datetime(2026, 8, 3, tzinfo=UTC),
            cells=[cell_context(cell_id=cell_id), cell_context(cell_id=cell_id, label="duplicate")],
            farm_data_version="test",
        )


def test_cell_context_rejects_invalid_geometry():
    with pytest.raises(ValidationError):
        IntercropCellContext(
            label="bad", area_hectares=1, palm_age_years=20,
            spacing_x_m=0, spacing_y_m=8, canopy_design="square",
        )
