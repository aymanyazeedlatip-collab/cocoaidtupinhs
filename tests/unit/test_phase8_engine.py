from __future__ import annotations

from app.engines.rehabilitation import RehabilitationEngine
from app.rehabilitation import repository
from tests.phase8_factory import prepare_phase8_dependencies, rehabilitation_request


def test_phase8_generates_six_scenarios_selects_feasible_and_persists():
    production, pest, intercrop, cell_id = prepare_phase8_dependencies()
    output = RehabilitationEngine().execute(
        rehabilitation_request(production, pest, intercrop, cell_id)
    ).output
    assert len(output.plan.scenarios) == 6
    assert {item.scenario_type for item in output.plan.scenarios} == {
        "no_action", "pest_management", "fertilization", "replanting",
        "intercropping", "combined_rehabilitation",
    }
    assert any(item.scenario_type == "no_action" and item.status == "feasible" for item in output.plan.scenarios)
    selected = next(item for item in output.plan.scenarios if item.scenario_type == output.plan.selected_scenario)
    assert selected.status == "feasible"
    assert output.plan.total_expected_cost_php == selected.total_cost_php
    assert output.summary.candidate_action_count == len(output.plan.actions)
    stored = repository.get_plan(output.plan.rehabilitation_plan_id)
    assert stored is not None
    assert len(stored["scenarios"]) == 6
    assert stored["selected_scenario"] == output.plan.selected_scenario


def test_phase8_budget_constraint_keeps_no_action_feasible():
    production, pest, intercrop, cell_id = prepare_phase8_dependencies()
    output = RehabilitationEngine().execute(rehabilitation_request(
        production, pest, intercrop, cell_id, total_budget_php=0,
    )).output
    assert output.plan.selected_scenario == "no_action"
    assert output.plan.total_expected_cost_php == 0
    assert all(
        item.status != "feasible" or item.scenario_type == "no_action"
        for item in output.plan.scenarios
    )


def test_phase8_confirmed_pest_allows_treatment_but_unconfirmed_does_not():
    production, pest, intercrop, cell_id = prepare_phase8_dependencies(confirmed_pest=True)
    confirmed = RehabilitationEngine().execute(
        rehabilitation_request(production, pest, intercrop, cell_id)
    ).output
    assert any(item.action_type.value == "pest_or_disease_treatment" for item in confirmed.plan.actions)

    production2, pest2, intercrop2, cell_id2 = prepare_phase8_dependencies(confirmed_pest=False)
    unconfirmed = RehabilitationEngine().execute(
        rehabilitation_request(production2, pest2, intercrop2, cell_id2)
    ).output
    assert not any(item.action_type.value == "pest_or_disease_treatment" for item in unconfirmed.plan.actions)
    assert any(
        item.action_type.value == "sanitation" and item.requires_field_confirmation
        for item in unconfirmed.plan.actions
    )
