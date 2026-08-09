from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.pest import NearbyConfirmedPestCase, PestObservation
from app.engines.pest_inference import PestInferenceEngine
from app.pest import repository
from tests.phase6_factory import pest_context, pest_request, prepare_phase6_production


def _assessment(output, pest_id):
    return next(item for item in output.assessments if item.profile.pest_profile_id == pest_id)


def test_phase6_engine_separates_conditional_and_expected_loss():
    production = prepare_phase6_production()
    request = pest_request(production, context=pest_context(
        waterlogging=True,
        drainage_quality=0.20,
        symptom_codes=["spear_leaf_wilting"],
    ))
    output = PestInferenceEngine().execute(request).output
    bud_rot = _assessment(output, "bud-nut-rot")
    assert bud_rot.outbreak_probability > 0.45
    assert bud_rot.expected_loss == pytest.approx(
        bud_rot.outbreak_probability * bud_rot.conditional_loss,
    )
    assert bud_rot.expected_loss <= bud_rot.conditional_loss
    assert output.summary.highest_risk_pest_id == "bud-nut-rot"
    assert len(output.assessments) == 5


def test_predicted_observation_is_stored_but_does_not_change_probability():
    production = prepare_phase6_production()
    engine = PestInferenceEngine()
    baseline = engine.execute(pest_request(
        production,
        pest_profile_ids=["coconut-scale-insect"],
    )).output
    observation = PestObservation(
        farm_id=production.forecast.farm_id,
        production_forecast_id=production.forecast.production_forecast_id,
        pest_profile_id="coconut-scale-insect",
        factor_code="scale_colonies",
        evidence_status="predicted",
        observed_at=datetime(2026, 8, 3, tzinfo=UTC),
        value=True,
        source_label="model-only test",
    )
    repository.save_observation(observation)
    with_observation = engine.execute(pest_request(
        production,
        pest_profile_ids=["coconut-scale-insect"],
        observation_ids=[observation.observation_id],
    )).output
    assert with_observation.assessments[0].outbreak_probability == pytest.approx(
        baseline.assessments[0].outbreak_probability,
    )
    audit = with_observation.evidence_audit[0]
    assert audit["used_for_probability"] is False


def test_confirmed_prevalence_increases_probability_and_links_bayesian_evidence():
    production = prepare_phase6_production()
    observation = PestObservation(
        farm_id=production.forecast.farm_id,
        production_forecast_id=production.forecast.production_forecast_id,
        pest_profile_id="coconut-scale-insect",
        factor_code="confirmed_prevalence",
        evidence_status="field_confirmed",
        observed_at=datetime(2026, 8, 3, tzinfo=UTC),
        value=0.30,
        unit="fraction",
        prevalence_fraction=0.30,
        source_label="field count",
    )
    _, bayesian_id = repository.save_observation(observation)
    assert bayesian_id is not None
    output = PestInferenceEngine().execute(pest_request(
        production,
        pest_profile_ids=["coconut-scale-insect"],
        observation_ids=[observation.observation_id],
    )).output
    assessment = output.assessments[0]
    assert assessment.outbreak_probability > 0.05
    assert output.summary.confirmed_evidence_count == 1
    assert output.evidence_audit[0]["bayesian_observation_id"] == str(bayesian_id)


def test_spatial_pressure_decays_with_distance():
    production = prepare_phase6_production()
    engine = PestInferenceEngine()
    close = engine.execute(pest_request(
        production,
        pest_profile_ids=["coconut-scale-insect"],
        nearby_confirmed_cases=[NearbyConfirmedPestCase(
            pest_profile_id="coconut-scale-insect", distance_m=100,
        )],
    )).output.assessments[0]
    far = engine.execute(pest_request(
        production,
        pest_profile_ids=["coconut-scale-insect"],
        nearby_confirmed_cases=[NearbyConfirmedPestCase(
            pest_profile_id="coconut-scale-insect", distance_m=10000,
        )],
    )).output.assessments[0]
    assert close.spatial_pressure > far.spatial_pressure
    assert close.outbreak_probability > far.outbreak_probability


def test_asiatic_palm_weevil_is_not_merged_with_legacy_red_palm_weevil():
    production = prepare_phase6_production()
    engine = PestInferenceEngine()
    with pytest.raises(Exception):
        engine.execute(pest_request(production, pest_profile_ids=["red_palm_weevil"]))
    output = engine.execute(pest_request(production, pest_profile_ids=["asiatic-palm-weevil"])).output
    assert output.assessments[0].profile.pest_profile_id == "asiatic-palm-weevil"
    assert "not merged" in output.taxonomy_notice.lower()
