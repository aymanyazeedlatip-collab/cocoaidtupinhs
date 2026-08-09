from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.rehabilitation import RehabilitationCellContext, RehabilitationTrigger


def test_phase8_cell_requires_exact_palm_conservation():
    with pytest.raises(ValidationError):
        RehabilitationCellContext(
            label="Bad cell", area_hectares=1, total_palms=10,
            healthy_bearing_palms=9, dead_palms=2,
        )


def test_phase8_predicted_evidence_cannot_be_confirmed_damage():
    with pytest.raises(ValidationError):
        RehabilitationTrigger(
            trigger_code="storm", source="weather", severity=0.8,
            evidence_status="predicted", confirmed_damage=True,
            description="Predicted event",
        )
