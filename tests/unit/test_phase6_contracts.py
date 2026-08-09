from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.contract_registry import contract_registry
from app.domain.pest import PestFarmContext
from tests.phase6_factory import pest_context


def test_phase6_contracts_are_registered():
    names = set(contract_registry.names())
    assert {
        "PestObservation", "PestFarmContext", "PestAssessmentRequest",
        "PestEvidenceContribution", "PestProfileAssessment", "PestEngineOutput",
    } <= names
    schema = contract_registry.schema("PestEngineOutput")
    assert schema["properties"]["schema_version"]["default"] == "3.0.0-draft.10"
    root = Path(__file__).resolve().parents[2]
    setup = (root / "setup.bat").read_text(encoding="utf-8")
    assert "python scripts\\verify_phase6.py" in setup


def test_pest_farm_context_rejects_counts_above_total():
    with pytest.raises(ValidationError):
        PestFarmContext(
            total_palms=10,
            young_palms=6,
            healthy_bearing_palms=6,
        )


def test_pest_farm_context_accepts_partial_inventory():
    context = pest_context(total_palms=500, young_palms=20)
    assert context.total_palms == 500
    assert context.young_palms == 20
