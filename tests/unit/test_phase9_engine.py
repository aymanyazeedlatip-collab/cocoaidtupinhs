from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.errors import EngineExecutionError
from app.decision_support import repository
from app.engines.decision_support import DecisionSupportEngine
from tests.phase9_factory import decision_request, prepare_phase9_records


def test_phase9_complete_network_persists_traceable_record():
    production, posterior, pest, intercrop, rehabilitation = prepare_phase9_records()
    output = DecisionSupportEngine().execute(
        decision_request(production, posterior, pest, intercrop, rehabilitation)
    ).output
    assert output.record.status == "completed"
    assert output.summary.succeeded_components == 5
    assert output.summary.data_completeness == 1
    assert output.record.overview.selected_rehabilitation_scenario == rehabilitation.plan.selected_scenario
    assert output.record.recommendations
    assert all(item.evidence for item in output.record.recommendations)
    assert any(item.category == "pest" for item in output.record.recommendations)
    assert any(item.category == "rehabilitation" for item in output.record.recommendations)
    stored = repository.get_run(output.record.analysis_run_id)
    assert stored is not None
    assert stored["status"] == "completed"
    assert len(stored["component_results"]) == 5
    assert len(stored["recommendations"]) == len(output.record.recommendations)


def test_phase9_continue_optional_discloses_missing_component():
    production, posterior, pest, intercrop, rehabilitation = prepare_phase9_records()
    output = DecisionSupportEngine().execute(decision_request(
        production, posterior, pest, intercrop, rehabilitation,
        posterior_id=None,
    )).output
    assert output.record.status == "partially_completed"
    bayesian = next(item for item in output.record.component_results if item.component == "bayesian")
    assert bayesian.status == "skipped"
    assert output.summary.data_completeness == pytest.approx(0.8)


def test_phase9_strict_policy_rejects_missing_record():
    production, posterior, pest, intercrop, rehabilitation = prepare_phase9_records()
    request = decision_request(
        production, posterior, pest, intercrop, rehabilitation,
        posterior_id=uuid4(), failure_policy="strict",
    )
    with pytest.raises(EngineExecutionError):
        DecisionSupportEngine().execute(request)
