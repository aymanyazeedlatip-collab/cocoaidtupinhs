from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.domain.bayesian import (
    BayesianDiagnostics,
    BayesianEvidenceObservation,
    BayesianEvidenceType,
    EvidenceAssimilationResult,
    PalmStateVector,
    PosteriorParameter,
    StatePosteriorInterval,
)
from app.domain.enums import EvidenceStatus
from app.domain.production import LegacyProductionIntervention, PredictiveInterval
from app.domain.units import UnitCode
from app.math.state import stochastic_transition_batch

BAYESIAN_PARAMETER_VERSION = "bayesian-farm-state-parameters-1.0.0"
STATE_NAMES = (
    "young", "healthy_bearing", "aging", "stressed",
    "infested_or_diseased", "rehabilitating", "dead",
)

RELIABILITY_WEIGHTS: dict[EvidenceStatus, float] = {
    EvidenceStatus.PREDICTED: 0.0,
    EvidenceStatus.SUSPECTED: 0.0,
    EvidenceStatus.FARMER_REPORTED: 0.35,
    EvidenceStatus.FIELD_CONFIRMED: 0.75,
    EvidenceStatus.EXPERT_CONFIRMED: 1.0,
}

INTERVENTION_EFFECTS: dict[LegacyProductionIntervention, dict[str, float]] = {
    LegacyProductionIntervention.NONE: {"pest": 0.0, "soil": 0.0, "replant": 0.0, "rehab": 0.0},
    LegacyProductionIntervention.MONITORING: {"pest": 0.08, "soil": 0.0, "replant": 0.0, "rehab": 0.03},
    LegacyProductionIntervention.PEST_CONTROL: {"pest": 0.38, "soil": 0.0, "replant": 0.0, "rehab": 0.12},
    LegacyProductionIntervention.SOIL_REHABILITATION: {"pest": 0.04, "soil": 0.32, "replant": 0.0, "rehab": 0.10},
    LegacyProductionIntervention.REPLANTING: {"pest": 0.03, "soil": 0.03, "replant": 0.18, "rehab": 0.06},
    LegacyProductionIntervention.COMBINED: {"pest": 0.32, "soil": 0.28, "replant": 0.24, "rehab": 0.18},
}


@dataclass(frozen=True)
class ParticleFilterInputs:
    initial_state: PalmStateVector
    base_production_tonnes: float
    base_pest_probability: float
    climate_stress_index: float
    forecast_rainfall_mm: float
    moisture_balance_index: float
    intervention: LegacyProductionIntervention
    horizon_months: int
    particle_count: int
    random_seed: int
    evidence: list[BayesianEvidenceObservation]
    prior_parameter_summaries: dict[str, dict[str, float]]
    prior_posterior_id: str | None = None


@dataclass(frozen=True)
class ParticleFilterResult:
    state: PalmStateVector
    state_intervals: list[StatePosteriorInterval]
    parameters: list[PosteriorParameter]
    production_distribution: PredictiveInterval
    probability_of_decline: float
    probability_of_recovery: float
    probability_of_tree_mortality: float
    probability_of_pest_outbreak: float
    uncertainty_sources: list[str]
    evidence_results: list[EvidenceAssimilationResult]
    diagnostics: BayesianDiagnostics
    warnings: list[str]


def _draw_beta(
    rng: np.random.Generator,
    count: int,
    name: str,
    default_alpha: float,
    default_beta: float,
    prior: dict[str, dict[str, float]],
) -> np.ndarray:
    values = prior.get(name, {})
    alpha = max(float(values.get("alpha", default_alpha)), 1e-3)
    beta = max(float(values.get("beta", default_beta)), 1e-3)
    return rng.beta(alpha, beta, count)


def _draw_lognormal(
    rng: np.random.Generator,
    count: int,
    name: str,
    default_mean: float,
    default_sigma: float,
    prior: dict[str, dict[str, float]],
) -> np.ndarray:
    values = prior.get(name, {})
    mean = float(values.get("log_mean", default_mean))
    sigma = max(float(values.get("log_sigma", default_sigma)), 1e-4)
    return rng.lognormal(mean, sigma, count)


def _draw_parameters(inputs: ParticleFilterInputs, rng: np.random.Generator) -> dict[str, np.ndarray]:
    n = inputs.particle_count
    prior = inputs.prior_parameter_summaries
    return {
        "weather_sensitivity": _draw_beta(rng, n, "weather_sensitivity", 3.5, 6.5, prior),
        "pest_sensitivity": _draw_beta(rng, n, "pest_sensitivity", 3.0, 7.0, prior),
        "annual_mortality_rate": _draw_beta(rng, n, "annual_mortality_rate", 1.5, 98.5, prior),
        "rehabilitation_success": _draw_beta(rng, n, "rehabilitation_success", 7.0, 3.0, prior),
        "soil_recovery_rate": _draw_beta(rng, n, "soil_recovery_rate", 5.0, 5.0, prior),
        "pest_loss_fraction": _draw_beta(rng, n, "pest_loss_fraction", 2.0, 8.0, prior),
        "production_multiplier": _draw_lognormal(rng, n, "production_multiplier", -0.5 * 0.12**2, 0.12, prior),
        "rainfall_bias_factor": _draw_lognormal(rng, n, "rainfall_bias_factor", -0.5 * 0.10**2, 0.10, prior),
    }


def _normalize_fraction(value: float, unit: UnitCode) -> float:
    return float(value) / 100.0 if unit == UnitCode.PERCENT else float(value)


def _normalize_harvest_tonnes(value: float, unit: UnitCode) -> float:
    return float(value) / 1000.0 if unit == UnitCode.KILOGRAM else float(value)


def _effective_sample_size(weights: np.ndarray) -> float:
    denominator = float(np.sum(np.square(weights)))
    return 0.0 if denominator <= 0 else 1.0 / denominator


def _systematic_resample(weights: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    n = len(weights)
    positions = (rng.random() + np.arange(n)) / n
    cumulative = np.cumsum(weights)
    cumulative[-1] = 1.0
    return np.searchsorted(cumulative, positions, side="right")


def _gaussian_log_likelihood(observed: float, predicted: np.ndarray, sigma: float) -> np.ndarray:
    sigma = max(float(sigma), 1e-9)
    z = (observed - predicted) / sigma
    return -0.5 * np.square(z) - np.log(sigma)


def _predicted_evidence(
    observation: BayesianEvidenceObservation,
    params: dict[str, np.ndarray],
    inputs: ParticleFilterInputs,
) -> tuple[float, np.ndarray, float]:
    state = inputs.initial_state
    total = max(state.total_palms, 1)
    initial_infested = state.infested_or_diseased / total
    climate = inputs.climate_stress_index
    if observation.evidence_type == BayesianEvidenceType.HARVEST:
        observed = _normalize_harvest_tonnes(observation.value, observation.unit)
        health = (
            state.healthy_bearing + 0.75 * state.aging + 0.45 * state.stressed
            + 0.25 * state.infested_or_diseased + 0.15 * state.rehabilitating + 0.05 * state.young
        ) / max(total - state.dead, 1)
        predicted = (
            inputs.base_production_tonnes * params["production_multiplier"] * (0.80 + 0.20 * state.soil_fertility_index)
            * np.clip(health, 0.10, 1.15)
            * (1.0 - params["pest_loss_fraction"] * initial_infested)
        )
        sigma = max(0.15 * max(observed, 1.0), 0.10 * max(inputs.base_production_tonnes, 1.0), 0.5)
    elif observation.evidence_type == BayesianEvidenceType.PEST_PREVALENCE:
        observed = _normalize_fraction(observation.value, observation.unit)
        predicted = np.clip(
            initial_infested + params["pest_sensitivity"] * inputs.base_pest_probability * (1.0 - initial_infested), 0, 1,
        )
        sigma = 0.12
    elif observation.evidence_type == BayesianEvidenceType.TREE_MORTALITY:
        observed = float(observation.value)
        predicted = total * params["annual_mortality_rate"] * (1.0 + climate * params["weather_sensitivity"])
        sigma = max(2.0, total * 0.03)
    elif observation.evidence_type == BayesianEvidenceType.STORM_DAMAGE:
        observed = _normalize_fraction(observation.value, observation.unit)
        predicted = np.clip(climate * params["weather_sensitivity"], 0, 1)
        sigma = 0.15
    elif observation.evidence_type == BayesianEvidenceType.REHABILITATION_COMPLETION:
        observed = _normalize_fraction(observation.value, observation.unit)
        predicted = params["rehabilitation_success"]
        sigma = 0.15
    elif observation.evidence_type == BayesianEvidenceType.ACTUAL_RAINFALL:
        observed = float(observation.value)
        predicted = max(inputs.forecast_rainfall_mm, 0.0) * params["rainfall_bias_factor"]
        sigma = max(20.0, observed * 0.20, inputs.forecast_rainfall_mm * 0.15)
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError(f"Unsupported evidence type: {observation.evidence_type}")
    return observed, predicted, sigma


def _resample_parameters(params: dict[str, np.ndarray], indexes: np.ndarray) -> None:
    for name in params:
        params[name] = params[name][indexes]


def _assimilate_evidence(
    params: dict[str, np.ndarray],
    inputs: ParticleFilterInputs,
    rng: np.random.Generator,
) -> tuple[list[EvidenceAssimilationResult], int, float, list[str]]:
    n = inputs.particle_count
    weights = np.full(n, 1.0 / n, dtype=float)
    results: list[EvidenceAssimilationResult] = []
    resampling_count = 0
    minimum_ess = float(n)
    warnings: list[str] = []

    for observation in sorted(inputs.evidence, key=lambda item: (item.observed_at, str(item.observation_id))):
        reliability = RELIABILITY_WEIGHTS[observation.evidence_status]
        if reliability <= 0:
            results.append(EvidenceAssimilationResult(
                observation_id=observation.observation_id,
                evidence_type=observation.evidence_type,
                evidence_status=observation.evidence_status,
                used_for_update=False,
                reliability_weight=0.0,
                explanation=(
                    "Predicted and suspected observations are retained for traceability but are not treated as Bayesian evidence."
                ),
            ))
            warnings.append(
                f"Observation {observation.observation_id} was not assimilated because its status is {observation.evidence_status.value}."
            )
            continue

        before = _effective_sample_size(weights)
        observed, predicted, sigma = _predicted_evidence(observation, params, inputs)
        log_like = reliability * _gaussian_log_likelihood(observed, predicted, sigma)
        log_like -= float(np.max(log_like))
        likelihood = np.exp(log_like)
        updated = weights * likelihood
        total = float(np.sum(updated))
        if not np.isfinite(total) or total <= 0:
            warnings.append(
                f"Observation {observation.observation_id} produced a degenerate likelihood and was not assimilated."
            )
            results.append(EvidenceAssimilationResult(
                observation_id=observation.observation_id,
                evidence_type=observation.evidence_type,
                evidence_status=observation.evidence_status,
                used_for_update=False,
                reliability_weight=reliability,
                effective_sample_size_before=before,
                effective_sample_size_after=before,
                explanation="Likelihood normalization failed; prior particles were preserved.",
            ))
            continue
        weights = updated / total
        after = _effective_sample_size(weights)
        minimum_ess = min(minimum_ess, after)
        resampled = False
        if after < 0.75 * n:
            indexes = _systematic_resample(weights, rng)
            _resample_parameters(params, indexes)
            weights.fill(1.0 / n)
            resampling_count += 1
            resampled = True
        results.append(EvidenceAssimilationResult(
            observation_id=observation.observation_id,
            evidence_type=observation.evidence_type,
            evidence_status=observation.evidence_status,
            used_for_update=True,
            reliability_weight=reliability,
            effective_sample_size_before=before,
            effective_sample_size_after=after,
            resampled=resampled,
            explanation=(
                "Evidence updated particle weights using a reliability-weighted Gaussian observation likelihood."
            ),
        ))

    # Carry any remaining non-uniform weights into an equally weighted posterior sample.
    if not np.allclose(weights, 1.0 / n):
        indexes = _systematic_resample(weights, rng)
        _resample_parameters(params, indexes)
        resampling_count += 1
    return results, resampling_count, minimum_ess, warnings


def _transition_matrices(
    params: dict[str, np.ndarray],
    climate: np.ndarray,
    pest_risk: np.ndarray,
    soil_fertility: np.ndarray,
    intervention: LegacyProductionIntervention,
) -> np.ndarray:
    n = len(climate)
    matrices = np.zeros((n, 7, 7), dtype=float)
    effect = INTERVENTION_EFFECTS[intervention]
    annual_mortality = params["annual_mortality_rate"]
    monthly_mortality = 1.0 - np.power(1.0 - np.clip(annual_mortality, 0, 0.35), 1.0 / 12.0)
    rehab_success = params["rehabilitation_success"]

    def set_row(source: int, destinations: dict[int, np.ndarray | float]) -> None:
        total = np.zeros(n, dtype=float)
        for destination, probability in destinations.items():
            values = np.broadcast_to(np.asarray(probability, dtype=float), (n,))
            values = np.clip(values, 0, 0.45)
            matrices[:, source, destination] = values
            total += values
        scale = np.minimum(1.0, 0.92 / np.maximum(total, 1e-12))
        for destination in destinations:
            matrices[:, source, destination] *= np.where(total > 0.92, scale, 1.0)
        matrices[:, source, source] = 1.0 - np.sum(matrices[:, source, :], axis=1)

    set_row(0, {
        1: 0.006,
        3: 0.004 + 0.025 * climate,
        4: 0.002 + 0.018 * pest_risk,
        6: monthly_mortality * (0.8 + 1.2 * climate),
    })
    set_row(1, {
        2: 0.003,
        3: 0.006 + 0.035 * climate,
        4: 0.003 + 0.025 * pest_risk * (1.0 - effect["pest"]),
        6: monthly_mortality * (0.8 + climate),
    })
    set_row(2, {
        3: 0.010 + 0.040 * climate,
        4: 0.005 + 0.030 * pest_risk * (1.0 - effect["pest"]),
        5: 0.004 + 0.012 * effect["rehab"],
        6: monthly_mortality * (1.5 + 1.5 * climate),
    })
    set_row(3, {
        1: 0.010 + 0.035 * soil_fertility * (0.5 + effect["soil"]),
        4: 0.008 + 0.030 * pest_risk * (1.0 - effect["pest"]),
        5: 0.004 + 0.025 * effect["rehab"],
        6: monthly_mortality * (1.0 + 2.0 * climate),
    })
    set_row(4, {
        1: 0.003 + 0.012 * effect["pest"],
        3: 0.018,
        5: 0.008 + 0.060 * effect["pest"] + 0.020 * effect["rehab"],
        6: monthly_mortality * (1.0 + 2.5 * pest_risk),
    })
    set_row(5, {
        1: 0.020 + 0.080 * rehab_success,
        3: 0.008 + 0.020 * climate,
        4: 0.003 + 0.010 * pest_risk,
        6: monthly_mortality * (0.8 + climate),
    })
    # Replanting converts vacant/dead planting positions into young palms while
    # preserving the total number of planting positions in every particle.
    set_row(6, {0: 0.015 * effect["replant"]})
    return matrices


def _state_score(counts: np.ndarray) -> np.ndarray:
    weights = np.array([0.05, 1.0, 0.75, 0.45, 0.25, 0.15, 0.0], dtype=float)
    return counts @ weights


def _quantile_interval(values: np.ndarray) -> PredictiveInterval:
    lower, median, upper = np.quantile(values.astype(float), [0.05, 0.50, 0.95])
    return PredictiveInterval(lower=max(float(lower), 0.0), median=max(float(median), 0.0), upper=max(float(upper), 0.0))


def _median_state(counts: np.ndarray, fertility: np.ndarray, water: np.ndarray, total: int) -> PalmStateVector:
    medians = np.rint(np.median(counts, axis=0)).astype(int)
    difference = total - int(medians.sum())
    medians[1] = max(0, medians[1] + difference)
    # If a negative correction exceeded healthy palms, reconcile across live states.
    if int(medians.sum()) != total:
        remainder = total - int(medians.sum())
        for index in (2, 3, 4, 5, 0, 6):
            if remainder == 0:
                break
            if remainder > 0:
                medians[index] += remainder
                remainder = 0
            else:
                take = min(medians[index], -remainder)
                medians[index] -= take
                remainder += take
    return PalmStateVector(
        young=int(medians[0]),
        healthy_bearing=int(medians[1]),
        aging=int(medians[2]),
        stressed=int(medians[3]),
        infested_or_diseased=int(medians[4]),
        rehabilitating=int(medians[5]),
        dead=int(medians[6]),
        soil_fertility_index=float(np.clip(np.median(fertility), 0, 1)),
        soil_water_index=float(np.clip(np.median(water), 0, 1)),
    )


def _state_intervals(counts: np.ndarray, fertility: np.ndarray, water: np.ndarray) -> list[StatePosteriorInterval]:
    results = [
        StatePosteriorInterval(state_variable=name, unit=UnitCode.COUNT, interval=_quantile_interval(counts[:, index]))
        for index, name in enumerate(STATE_NAMES)
    ]
    results.extend([
        StatePosteriorInterval(
            state_variable="soil_fertility_index", unit=UnitCode.INDEX_0_1, interval=_quantile_interval(fertility),
        ),
        StatePosteriorInterval(
            state_variable="soil_water_index", unit=UnitCode.INDEX_0_1, interval=_quantile_interval(water),
        ),
    ])
    return results


def _beta_moment_match(values: np.ndarray) -> tuple[float, float]:
    mean = float(np.mean(values))
    variance = float(np.var(values, ddof=1)) if len(values) > 1 else 0.0
    maximum = mean * (1.0 - mean)
    if variance <= 1e-10 or variance >= maximum:
        concentration = 200.0
    else:
        concentration = maximum / variance - 1.0
    alpha = max(mean * concentration, 1e-3)
    beta = max((1.0 - mean) * concentration, 1e-3)
    return alpha, beta


def _parameter_summaries(params: dict[str, np.ndarray]) -> list[PosteriorParameter]:
    summaries: list[PosteriorParameter] = []
    for name, values in params.items():
        interval = _quantile_interval(values)
        if name in {
            "weather_sensitivity", "pest_sensitivity", "annual_mortality_rate",
            "rehabilitation_success", "soil_recovery_rate", "pest_loss_fraction",
        }:
            alpha, beta = _beta_moment_match(values)
            distribution = "beta_moment_matched"
            parameters = {"alpha": alpha, "beta": beta}
        else:
            logs = np.log(np.clip(values, 1e-12, None))
            distribution = "lognormal_moment_matched"
            parameters = {"log_mean": float(np.mean(logs)), "log_sigma": float(np.std(logs, ddof=1))}
        summaries.append(PosteriorParameter(
            name=name,
            distribution=distribution,
            parameters=parameters,
            posterior_mean=float(np.mean(values)),
            credible_interval=interval,
        ))
    return summaries


def _uncertainty_sources(params: dict[str, np.ndarray], production: np.ndarray) -> list[str]:
    ranked: list[tuple[float, str]] = []
    for name, values in params.items():
        if float(np.std(values)) <= 1e-12 or float(np.std(production)) <= 1e-12:
            correlation = 0.0
        else:
            correlation = float(np.corrcoef(values, production)[0, 1])
            if not np.isfinite(correlation):
                correlation = 0.0
        ranked.append((abs(correlation), name))
    ranked.sort(reverse=True)
    return [name for _, name in ranked[:5]] + ["stochastic_palm_state_transitions"]


def run_particle_filter(inputs: ParticleFilterInputs) -> ParticleFilterResult:
    rng = np.random.default_rng(inputs.random_seed)
    params = _draw_parameters(inputs, rng)
    evidence_results, resampling_count, minimum_ess, warnings = _assimilate_evidence(params, inputs, rng)

    initial = np.array([
        inputs.initial_state.young,
        inputs.initial_state.healthy_bearing,
        inputs.initial_state.aging,
        inputs.initial_state.stressed,
        inputs.initial_state.infested_or_diseased,
        inputs.initial_state.rehabilitating,
        inputs.initial_state.dead,
    ], dtype=int)
    counts = np.broadcast_to(initial, (inputs.particle_count, 7)).copy()
    initial_total = int(initial.sum())
    initial_score = float(_state_score(initial[None, :])[0])
    initial_dead = int(initial[6])
    initial_infested_fraction = initial[4] / max(initial_total, 1)
    fertility = np.full(inputs.particle_count, inputs.initial_state.soil_fertility_index, dtype=float)
    water = np.full(inputs.particle_count, inputs.initial_state.soil_water_index, dtype=float)
    effect = INTERVENTION_EFFECTS[inputs.intervention]

    target_water = np.clip(
        0.50 + 0.30 * inputs.moisture_balance_index + min(max(inputs.forecast_rainfall_mm, 0.0), 800.0) / 1600.0,
        0.05, 0.95,
    )
    for month in range(inputs.horizon_months):
        seasonal = 0.06 * np.sin(2.0 * np.pi * month / 12.0)
        climate = np.clip(
            inputs.climate_stress_index * (0.65 + params["weather_sensitivity"]) + seasonal
            + rng.normal(0.0, 0.025, inputs.particle_count),
            0, 1,
        )
        current_infested = counts[:, 4] / np.maximum(counts.sum(axis=1), 1)
        pest_risk = np.clip(
            inputs.base_pest_probability * (0.70 + params["pest_sensitivity"])
            + 0.30 * current_infested + 0.12 * climate,
            0, 1,
        )
        matrices = _transition_matrices(params, climate, pest_risk, fertility, inputs.intervention)
        counts = stochastic_transition_batch(counts, matrices, rng)

        water += 0.18 * params["weather_sensitivity"] * (target_water - water)
        water -= 0.025 * climate
        water += rng.normal(0.0, 0.012, inputs.particle_count)
        water = np.clip(water, 0, 1)

        fertility += 0.018 * effect["soil"] * params["soil_recovery_rate"]
        fertility -= 0.004 + 0.006 * climate
        fertility += rng.normal(0.0, 0.006, inputs.particle_count)
        fertility = np.clip(fertility, 0, 1)

    totals = counts.sum(axis=1)
    conserved = bool(np.all(totals == initial_total))
    if not conserved:
        raise RuntimeError("Particle transitions failed to conserve total planting positions")

    final_score = _state_score(counts)
    score_ratio = final_score / max(initial_score, 1.0)
    infested_fraction = counts[:, 4] / np.maximum(totals, 1)
    dead_increase = counts[:, 6] > initial_dead
    # The Phase 4 baseline already incorporates farm soil and weather features.
    # Bayesian propagation therefore applies *relative* state change rather than
    # multiplying by the absolute initial indices a second time.
    initial_fertility = float(inputs.initial_state.soil_fertility_index)
    initial_water = float(inputs.initial_state.soil_water_index)
    soil_factor = np.clip(1.0 + 0.25 * (fertility - initial_fertility), 0.75, 1.20)
    water_factor = np.clip(1.0 + 0.20 * (water - initial_water), 0.75, 1.20)
    pest_factor = 1.0 - params["pest_loss_fraction"] * infested_fraction
    production = (
        inputs.base_production_tonnes * params["production_multiplier"]
        * np.clip(score_ratio, 0.15, 1.35) * soil_factor * water_factor * np.clip(pest_factor, 0.35, 1.0)
    )
    production = np.clip(production, 0, None)

    recovery = (final_score > initial_score) & ((counts[:, 3] + counts[:, 4]) < (initial[3] + initial[4]))
    outbreak_threshold = max(0.10, initial_infested_fraction + 0.05)
    pest_outbreak = infested_fraction >= outbreak_threshold

    posterior_state = _median_state(counts, fertility, water, initial_total)
    evidence_used = sum(item.used_for_update for item in evidence_results)
    diagnostics = BayesianDiagnostics(
        particle_count=inputs.particle_count,
        horizon_months=inputs.horizon_months,
        random_seed=inputs.random_seed,
        prior_posterior_id=inputs.prior_posterior_id,
        evidence_count_requested=len(inputs.evidence),
        evidence_count_used=evidence_used,
        resampling_count=resampling_count,
        minimum_effective_sample_size=float(minimum_ess),
        palm_count_conserved=conserved,
    )
    return ParticleFilterResult(
        state=posterior_state,
        state_intervals=_state_intervals(counts, fertility, water),
        parameters=_parameter_summaries(params),
        production_distribution=_quantile_interval(production),
        probability_of_decline=float(np.mean(production < inputs.base_production_tonnes)),
        probability_of_recovery=float(np.mean(recovery)),
        probability_of_tree_mortality=float(np.mean(dead_increase)),
        probability_of_pest_outbreak=float(np.mean(pest_outbreak)),
        uncertainty_sources=_uncertainty_sources(params, production),
        evidence_results=evidence_results,
        diagnostics=diagnostics,
        warnings=list(dict.fromkeys(warnings)),
    )
