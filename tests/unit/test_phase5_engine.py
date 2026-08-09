from __future__ import annotations

from datetime import UTC, datetime

from app.bayesian import repository
from app.domain.bayesian import BayesianEvidenceObservation
from app.engines.bayesian import BayesianEngine
from app.engines.registry import engine_registry
from app.production import repository as production_repository
from tests.phase5_factory import bayesian_request, prepare_phase5_production


def test_bayesian_engine_is_registered_reproducible_and_updates_production_layer():
    production = prepare_phase5_production()
    forecast_id = production.forecast.production_forecast_id
    engine = BayesianEngine()
    first = engine.execute(bayesian_request(forecast_id, random_seed=44)).output
    second = engine.execute(bayesian_request(forecast_id, random_seed=44)).output
    assert engine_registry.descriptor("v3.bayesian").availability.value == "available"
    assert first.posterior.production_distribution == second.posterior.production_distribution
    assert first.posterior.state == second.posterior.state
    assert first.diagnostics.palm_count_conserved is True
    stored = production_repository.get_forecast(forecast_id)
    assert stored["posterior_status"] == "available"
    assert stored["posterior"]["median"] == first.posterior.production_distribution.median
    assert repository.summary()["bayesian_posteriors"] == 2


def test_bayesian_engine_evidence_gate_and_sequential_update():
    production = prepare_phase5_production()
    forecast = production.forecast
    predicted = BayesianEvidenceObservation(
        farm_id=forecast.farm_id,
        production_forecast_id=forecast.production_forecast_id,
        evidence_type="storm_damage",
        evidence_status="predicted",
        observed_at=datetime(2026, 8, 4, tzinfo=UTC),
        value=0.8,
        unit="fraction",
    )
    confirmed = BayesianEvidenceObservation(
        farm_id=forecast.farm_id,
        production_forecast_id=forecast.production_forecast_id,
        evidence_type="pest_prevalence",
        evidence_status="field_confirmed",
        observed_at=datetime(2026, 8, 5, tzinfo=UTC),
        value=0.35,
        unit="fraction",
    )
    repository.save_observation(predicted)
    repository.save_observation(confirmed)
    first = BayesianEngine().execute(bayesian_request(
        forecast.production_forecast_id,
        evidence_observation_ids=[predicted.observation_id, confirmed.observation_id],
        random_seed=77,
    )).output
    assert first.diagnostics.evidence_count_requested == 2
    assert first.diagnostics.evidence_count_used == 1
    assert [item.used_for_update for item in first.evidence_results] == [False, True]

    sequential = BayesianEngine().execute(bayesian_request(
        forecast.production_forecast_id,
        initial_state=None,
        prior_posterior_id=first.posterior.posterior_id,
        evidence_observation_ids=[],
        baseline_state_date=datetime(2027, 8, 3, tzinfo=UTC),
        horizon_months=6,
        random_seed=78,
    )).output
    assert sequential.posterior.prior_posterior_id == first.posterior.posterior_id
    assert sequential.diagnostics.prior_posterior_id == first.posterior.posterior_id
