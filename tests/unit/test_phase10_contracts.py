from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.coco_pilot import CocoPilotRequest, FormalReportRequest


def test_phase10_contract_modes_and_aware_time():
    request = CocoPilotRequest(
        analysis_run_id=uuid4(), mode="risk_summary", provider_mode="deterministic",
        generated_at=datetime(2026, 8, 4, tzinfo=UTC),
    )
    assert request.schema_version == "3.0.0-draft.10"
    with pytest.raises(ValueError):
        CocoPilotRequest(
            analysis_run_id=uuid4(), mode="risk_summary", provider_mode="deterministic",
            generated_at=datetime(2026, 8, 4),
        )


def test_phase10_formal_report_contract_rejects_unknown_format():
    with pytest.raises(ValueError):
        FormalReportRequest(
            analysis_run_id=uuid4(), report_format="html",
            generated_at=datetime(2026, 8, 4, tzinfo=UTC),
        )
