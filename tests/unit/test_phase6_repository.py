from __future__ import annotations

from app.engines.pest_inference import PestInferenceEngine
from app.pest import repository
from tests.phase6_factory import pest_request, prepare_phase6_production


def test_phase6_assessment_persistence_includes_contributions_and_actions():
    production = prepare_phase6_production()
    output = PestInferenceEngine().execute(pest_request(
        production,
        pest_profile_ids=["rhinoceros-beetle"],
    )).output
    assessment_id = output.assessments[0].assessment_id
    saved = repository.get_assessment(assessment_id)
    assert saved is not None
    assert saved["pest_profile_id"] == "rhinoceros-beetle"
    assert saved["evidence_contributions"]
    assert saved["management_actions"]
    counts = repository.summary()
    assert counts["pest_assessment_runs"] == 1
    assert counts["pest_assessments_v3"] == 1
