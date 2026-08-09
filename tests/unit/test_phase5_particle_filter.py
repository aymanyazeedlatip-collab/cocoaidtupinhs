from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.bayesian.particle_filter import ParticleFilterInputs, run_particle_filter
from app.domain.bayesian import BayesianEvidenceObservation
from tests.phase5_factory import initial_state


def _inputs(**updates):
    payload = dict(
        initial_state=initial_state(),
        base_production_tonnes=12.0,
        base_pest_probability=0.12,
        climate_stress_index=0.25,
        forecast_rainfall_mm=45.0,
        moisture_balance_index=0.10,
        intervention="none",
        horizon_months=12,
        particle_count=400,
        random_seed=99,
        evidence=[],
        prior_parameter_summaries={},
    )
    payload.update(updates)
    return ParticleFilterInputs(**payload)


def test_particle_filter_is_seed_deterministic_and_conserves_planting_positions():
    first = run_particle_filter(_inputs())
    second = run_particle_filter(_inputs())
    assert first.production_distribution == second.production_distribution
    assert first.state == second.state
    assert first.diagnostics.palm_count_conserved is True
    assert first.state.total_palms == initial_state().total_palms
    assert 0 <= first.probability_of_decline <= 1
    assert 0 <= first.probability_of_recovery <= 1
    assert len(first.parameters) == 8
    assert len(first.state_intervals) == 9


def test_predicted_and_suspected_observations_do_not_update_particles():
    predicted = BayesianEvidenceObservation(
        observation_id=uuid4(),
        farm_id=uuid4(),
        evidence_type="pest_prevalence",
        evidence_status="predicted",
        observed_at=datetime.now(UTC),
        value=0.9,
        unit="fraction",
    )
    result = run_particle_filter(_inputs(evidence=[predicted]))
    assert result.diagnostics.evidence_count_used == 0
    assert result.evidence_results[0].used_for_update is False
    assert any("not assimilated" in warning for warning in result.warnings)


def test_confirmed_evidence_changes_posterior_parameter_distribution():
    no_evidence = run_particle_filter(_inputs())
    confirmed = BayesianEvidenceObservation(
        observation_id=uuid4(),
        farm_id=uuid4(),
        evidence_type="pest_prevalence",
        evidence_status="expert_confirmed",
        observed_at=datetime.now(UTC),
        value=0.65,
        unit="fraction",
    )
    updated = run_particle_filter(_inputs(evidence=[confirmed]))
    before = {item.name: item.posterior_mean for item in no_evidence.parameters}
    after = {item.name: item.posterior_mean for item in updated.parameters}
    assert updated.diagnostics.evidence_count_used == 1
    assert after["pest_sensitivity"] > before["pest_sensitivity"]


def test_no_extreme_case_does_not_double_penalize_phase4_baseline():
    result = run_particle_filter(_inputs(climate_stress_index=0.10, base_pest_probability=0.05))
    assert result.production_distribution.median >= 6.0
    assert result.production_distribution.median <= 18.0
