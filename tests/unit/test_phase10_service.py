from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.coco_pilot.service import CocoPilotService
from app.domain.coco_pilot import CocoPilotRequest
from app.engines.decision_support import DecisionSupportEngine
from tests.phase9_factory import decision_request, prepare_phase9_records


def test_phase10_deterministic_explanation_is_grounded_and_persisted():
    production, posterior, pest, intercrop, rehabilitation = prepare_phase9_records()
    decision = DecisionSupportEngine().execute(
        decision_request(production, posterior, pest, intercrop, rehabilitation)
    ).output
    result = asyncio.run(CocoPilotService().explain(CocoPilotRequest(
        analysis_run_id=decision.record.analysis_run_id,
        mode="report_narrative",
        provider_mode="deterministic",
        generated_at=datetime(2026, 8, 4, 5, tzinfo=UTC),
    )))
    assert result.status == "completed"
    assert result.provider == "deterministic"
    assert result.citations
    assert result.redaction_summary.farmer_names_included is False
    assert result.redaction_summary.raw_farmer_records_included is False
    assert "chemical dosage" in " ".join(result.limitations).lower()
    assert "Sources:" in result.full_text

    comparison = asyncio.run(CocoPilotService().explain(CocoPilotRequest(
        analysis_run_id=decision.record.analysis_run_id,
        mode="compare_scenarios",
        provider_mode="deterministic",
        generated_at=datetime(2026, 8, 4, 5, 5, tzinfo=UTC),
    )))
    assert len(comparison.bullets) == 6
    assert any("No Action" in bullet for bullet in comparison.bullets)
