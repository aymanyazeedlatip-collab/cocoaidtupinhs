from __future__ import annotations

from app.engines.intercropping import IntercroppingEngine
from app.intercropping import repository
from tests.phase7_factory import (
    intercropping_request, prepare_high_bud_rot_pest_run, prepare_phase7_production,
)


def _assessment(output, candidate_id: str):
    return next(item for item in output.assessments if item.candidate.candidate_id == candidate_id)


def test_phase7_scores_candidates_caps_hard_constraints_and_persists():
    production = prepare_phase7_production()
    output = IntercroppingEngine().execute(intercropping_request(production)).output
    cacao = _assessment(output, "cacao")
    sugarcane = _assessment(output, "sugarcane")
    assert output.summary.total_assessment_count == 4
    assert cacao.economic_potential.status == "available"
    assert cacao.economic_potential.gross_revenue_lower_php <= cacao.economic_potential.gross_revenue_median_php
    assert sugarcane.hard_constraint_passed is False
    assert sugarcane.suitability_score <= 40
    assert all(0 <= item.suitability_score <= 100 for item in output.assessments)
    persisted = repository.get_assessment(cacao.assessment_id)
    assert persisted is not None
    assert persisted["candidate_id"] == "cacao"
    assert len(persisted["components"]) == 9


def test_phase7_pest_run_increases_candidate_specific_conflict_penalty():
    production = prepare_phase7_production()
    engine = IntercroppingEngine()
    baseline = engine.execute(intercropping_request(production, candidate_ids=["cacao"])).output
    pest = prepare_high_bud_rot_pest_run(production)
    conditioned = engine.execute(intercropping_request(
        production, candidate_ids=["cacao"], pest_assessment_run_id=pest.run_id,
    )).output
    before = baseline.assessments[0]
    after = conditioned.assessments[0]
    assert after.pest_conflict_risk > before.pest_conflict_risk
    assert after.suitability_score < before.suitability_score


def test_phase7_no_economic_profile_is_explicitly_unavailable():
    production = prepare_phase7_production()
    output = IntercroppingEngine().execute(intercropping_request(
        production, candidate_ids=["banana"],
    )).output
    economic = output.assessments[0].economic_potential
    assert economic.status == "not_available"
    assert economic.gross_revenue_median_php is None
