from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

from app.climate.projections import year_climate_parameters
from app.core.config import settings
from app.math.bayes import evaluate_pest_risk
from app.math.state import SCENARIO_EFFECTS, STATES, stochastic_transition_batch, transition_matrices
from app.math.suitability import suitability_index
from app.models.registry import model_metadata, predict_many
from app.schemas.analysis import PestRiskRequest, SimulationRequest, SuitabilityRequest
from app.schemas.farm import FarmCreate

INTERVENTION_COST = {
    "no_intervention": 0.0,
    "monitoring": 0.018,
    "pest_management": 0.055,
    "soil_rehabilitation": 0.075,
    "partial_replanting": 0.11,
    "combined_rehabilitation": 0.145,
}

INTERVENTIONS = list(INTERVENTION_COST)
EVENTS = np.array(["normal", "drought", "extreme_rain", "heat_stress", "typhoon"], dtype=object)


@dataclass(frozen=True)
class PreparedSimulationContext:
    initial_counts: np.ndarray
    suitability: float
    base_pest: float
    pest_ml_probability: float | None
    suitability_ml_score: float | None
    ml_corrections: dict[str, float]
    model_versions: dict[str, str]
    fallback_models: list[str]


def _pest_ml_row(farm: FarmCreate, rainfall: float = 2100, temperature: float = 27.0, humidity: float = 78.0) -> dict[str, Any]:
    s = farm.symptoms
    return {
        "annual_rainfall_mm": rainfall,
        "mean_temperature_c": temperature,
        "relative_humidity_percent": humidity,
        "average_tree_age": farm.trees.average_age_years,
        "yellowing": int(s.yellowing),
        "crown_decline": int(s.crown_decline),
        "frond_cuts": int(s.frond_cuts),
        "visible_scale_insects": int(s.visible_scale_insects),
        "rhinoceros_beetle_damage": int(s.rhinoceros_beetle_damage),
        "premature_nut_fall": int(s.premature_nut_fall),
        "nearby_reports": int(s.nearby_reports),
        "symptom_severity": s.severity,
        "pest_control": int(farm.management.pest_control),
    }


def _suitability_ml_row(farm: FarmCreate, annual_rainfall: float = 2200, temp: float = 27.0) -> dict[str, Any]:
    st = farm.soil_terrain
    return {
        "annual_rainfall_mm": annual_rainfall,
        "mean_temperature_c": temp,
        "relative_humidity_percent": 78,
        "elevation_m": st.elevation_m,
        "slope_degrees": st.slope_degrees,
        "soil_ph": st.soil_ph,
        "nitrogen_index": st.nitrogen_index,
        "phosphorus_index": st.phosphorus_index,
        "potassium_index": st.potassium_index,
        "drainage_index": st.drainage_index,
        "drought_exposure": 0.18,
        "typhoon_exposure": 0.12,
    }


def _production_ml_row(
    farm: FarmCreate,
    counts: np.ndarray,
    climate: dict[str, float],
    suitability: float,
    pest_probability: float,
    intervention: str,
    severity: float = 0.1,
) -> dict[str, Any]:
    st = farm.soil_terrain
    event_intervention = {
        "no_intervention": "none",
        "monitoring": "monitoring",
        "pest_management": "pest_control",
        "soil_rehabilitation": "soil_rehabilitation",
        "partial_replanting": "replanting",
        "combined_rehabilitation": "combined",
    }[intervention]
    return {
        "farm_area_hectares": farm.area_hectares,
        "productive_trees": counts[1],
        "aging_trees": counts[2],
        "stressed_trees": counts[3],
        "infested_trees": counts[4],
        "recovering_trees": counts[5],
        "annual_rainfall_mm": climate["rainfall"],
        "mean_temperature_c": climate["temperature"],
        "relative_humidity_percent": climate["humidity"],
        "drought_exposure": climate["drought"],
        "weather_severity": severity,
        "soil_ph": st.soil_ph,
        "nitrogen_index": st.nitrogen_index,
        "phosphorus_index": st.phosphorus_index,
        "potassium_index": st.potassium_index,
        "suitability_score": suitability,
        "pest_probability": pest_probability,
        "variety": farm.trees.variety if farm.trees.variety != "Unknown" else "Tall",
        "intervention": event_intervention,
    }


def _initial_counts(farm: FarmCreate) -> np.ndarray:
    t = farm.trees
    return np.array([t.young, t.productive, t.aging, t.stressed, t.infested, t.recovering, t.dead], dtype=int)


def prepare_simulation_context(farm: FarmCreate) -> PreparedSimulationContext:
    initial = _initial_counts(farm)
    suit_request = SuitabilityRequest(
        soil_terrain=farm.soil_terrain,
        annual_rainfall_mm=2200,
        mean_temperature_c=27,
        humidity_percent=78,
        drought_exposure=0.18,
        climate_stress=0.15,
    )
    suitability_ml = predict_many("suitability", [_suitability_ml_row(farm)])[0]
    suitability = suitability_index(suit_request, suitability_ml)["score"]

    pest_input = PestRiskRequest(
        prior_probability=0.15,
        symptoms=farm.symptoms,
        humidity_percent=78,
        rainfall_mm_month=185,
        average_tree_age=farm.trees.average_age_years,
    )
    pest_ml = predict_many("pest", [_pest_ml_row(farm)])[0]
    base_pest = evaluate_pest_risk(pest_input, pest_ml)["posterior_probability"]

    typical_climate = {"rainfall": 2200.0, "temperature": 27.0, "humidity": 78.0, "drought": 0.18, "stress": 0.15}
    rows = [
        _production_ml_row(farm, initial, typical_climate, suitability, base_pest, intervention)
        for intervention in INTERVENTIONS
    ]
    model_values = predict_many("production", rows)
    baseline = max(farm.production.annual_production_tons, 0.1)
    corrections: dict[str, float] = {}
    for intervention, value in zip(INTERVENTIONS, model_values, strict=True):
        if value is None or not np.isfinite(value) or value <= 0:
            corrections[intervention] = 1.0
        else:
            ratio = float(np.clip(value / baseline, 0.65, 1.35))
            # The synthetic ML model acts only as a bounded correction. The explicit
            # biological model remains dominant.
            corrections[intervention] = float(0.90 + 0.10 * ratio)

    metadata = model_metadata()
    return PreparedSimulationContext(
        initial_counts=initial,
        suitability=float(suitability),
        base_pest=float(base_pest),
        pest_ml_probability=float(pest_ml) if pest_ml is not None else None,
        suitability_ml_score=float(suitability_ml) if suitability_ml is not None else None,
        ml_corrections=corrections,
        model_versions={name: item["version"] for name, item in metadata.items()},
        fallback_models=[name for name, item in metadata.items() if item.get("fallback_active")],
    )


def _event_probabilities(year: int, scenario: str, latitude: float) -> tuple[np.ndarray, dict[str, float]]:
    params = year_climate_parameters(year, scenario, latitude)
    risks = np.array([
        params["drought_probability"],
        params["extreme_rain_probability"],
        params["heat_probability"],
        params["typhoon_probability"],
    ], dtype=float)
    if risks.sum() > 0.82:
        risks *= 0.82 / risks.sum()
    probabilities = np.concatenate(([1 - risks.sum()], risks))
    probabilities /= probabilities.sum()
    return probabilities, params


def _sample_weather_year(
    runs: int,
    year: int,
    scenario: str,
    latitude: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    probabilities, params = _event_probabilities(year, scenario, latitude)
    codes = rng.choice(len(EVENTS), size=runs, p=probabilities)
    events = EVENTS[codes]
    normal_severity = rng.beta(1.2, 6.0, size=runs)
    event_severity = rng.beta(2.0, 2.8, size=runs)
    severity = np.where(codes == 0, normal_severity, event_severity)

    temperature = 27.0 + params["temperature_anomaly_c"] + rng.normal(0, 0.35, size=runs)
    rainfall = 2200 * params["rainfall_ratio"] * rng.lognormal(-0.5 * 0.10**2, 0.10, size=runs)
    drought = np.clip(0.12 + np.maximum(0, temperature - 28) * 0.08 + np.maximum(0, 1800 - rainfall) / 2600, 0, 1)

    drought_mask = codes == 1
    rain_mask = codes == 2
    heat_mask = codes == 3
    typhoon_mask = codes == 4
    rainfall[drought_mask] *= 1 - 0.25 - 0.35 * severity[drought_mask]
    drought[drought_mask] = np.minimum(1.0, drought[drought_mask] + 0.35 + 0.35 * severity[drought_mask])
    rainfall[rain_mask] *= 1 + 0.25 + 0.55 * severity[rain_mask]
    temperature[heat_mask] += 0.6 + 1.3 * severity[heat_mask]
    drought[heat_mask] = np.minimum(1.0, drought[heat_mask] + 0.15 + 0.25 * severity[heat_mask])
    rainfall[typhoon_mask] *= 1 + 0.15 + 0.45 * severity[typhoon_mask]

    humidity = np.clip(72 + rainfall / 300 + rng.normal(0, 2, size=runs), 52, 96)
    stress = np.clip(
        0.10 + drought * 0.55 + np.maximum(0, temperature - 29) * 0.08
        + np.where(codes == 0, 0, 0.20 * severity),
        0,
        1,
    )
    return events, severity, {
        "temperature": temperature,
        "rainfall": rainfall,
        "humidity": humidity,
        "drought": drought,
        "stress": stress,
    }, params


def _annual_replant_fraction(request: SimulationRequest, year_index: int) -> float:
    if request.intervention not in {"partial_replanting", "combined_rehabilitation"}:
        return 0.0
    scenario_rate = SCENARIO_EFFECTS[request.intervention]["replant"]
    declared_plan = request.farm.management.replanting_percent / 100 / 5
    active_rate = min(0.08, max(scenario_rate, declared_plan))
    return active_rate if year_index < 10 else min(0.02 if request.intervention == "combined_rehabilitation" else 0.012, active_rate * 0.40)


def _production_vector(
    request: SimulationRequest,
    counts: np.ndarray,
    initial: np.ndarray,
    suitability: float,
    climate: dict[str, np.ndarray],
    pest_probability: np.ndarray,
    events: np.ndarray,
    severity: np.ndarray,
    rng: np.random.Generator,
    ml_correction: float,
) -> np.ndarray:
    total = np.maximum(1, counts.sum(axis=1))
    # Production is anchored to the entered baseline, but tree composition must still
    # matter. A farm with many infested or vacant positions cannot be treated as
    # equivalent to a healthy farm merely because both users entered the same recent
    # production. These reference shares are explicit development assumptions and are
    # reported as limitations rather than hidden calibration constants.
    productive_equivalent = counts[:, 1] + 0.58 * counts[:, 2] + 0.35 * counts[:, 5]
    reference_productive_equivalent = np.maximum(1.0, total * 0.68)
    tree_factor = np.clip(productive_equivalent / reference_productive_equivalent, 0.30, 1.20)

    current_health = np.exp(
        -0.85 * counts[:, 3] / total
        -1.15 * counts[:, 4] / total
        -0.70 * counts[:, 6] / total
    )
    reference_health = math.exp(-0.85 * 0.07 - 1.15 * 0.04 - 0.70 * 0.03)
    health_factor = np.clip(current_health / reference_health, 0.40, 1.20)

    # Current observed production already reflects the farm's normal climate and site.
    # Only departure from a reference stress level is applied, avoiding an artificial
    # immediate drop at the first simulated year.
    resilience = 1.15 - 0.30 * suitability
    climate_factor = np.clip(np.exp(-0.55 * (climate["stress"] - 0.15) * resilience), 0.45, 1.25)
    pest_factor = np.clip(np.exp(-0.30 * (pest_probability - 0.15)), 0.65, 1.12)

    event_factor = np.ones(len(counts), dtype=float)
    event_factor = np.where(events == "typhoon", np.maximum(0.25, 1 - 0.25 - 0.42 * severity), event_factor)
    event_factor = np.where(events == "drought", np.maximum(0.45, 1 - 0.12 - 0.25 * severity), event_factor)
    event_factor = np.where(events == "extreme_rain", np.maximum(0.60, 1 - 0.05 - 0.13 * severity), event_factor)
    event_factor = np.where(events == "heat_stress", np.maximum(0.55, 1 - 0.08 - 0.18 * severity), event_factor)

    effects = SCENARIO_EFFECTS[request.intervention]
    management_factor = 1 + effects["soil"] * 0.48 + effects["pest"] * 0.20 + effects["recovery"] * 0.15
    expected = (
        request.farm.production.annual_production_tons
        * tree_factor
        * health_factor
        * climate_factor
        * pest_factor
        * event_factor
        * management_factor
        * ml_correction
    )
    sigma = 0.07 + 0.09 * climate["stress"]
    noise = rng.lognormal(-0.5 * sigma**2, sigma)
    return np.maximum(0, expected * noise)


def _safe_correlation(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def run_simulation(request: SimulationRequest, context: PreparedSimulationContext | None = None) -> dict[str, Any]:
    context = context or prepare_simulation_context(request.farm)
    initial = context.initial_counts
    years = list(range(request.start_year, request.end_year + 1))
    n_years = len(years)
    runs = request.runs

    counts = np.broadcast_to(initial, (runs, len(STATES))).copy()
    production = np.zeros((runs, n_years), dtype=float)
    state_history = np.zeros((runs, n_years, len(STATES)), dtype=np.int32)
    major_loss_years = np.zeros(runs, dtype=np.int16)
    event_counts = {event: np.zeros(runs, dtype=np.int16) for event in EVENTS[1:]}
    outbreak_counts = np.zeros(runs, dtype=np.int16)
    event_counter: Counter[str] = Counter()
    sample_events: list[dict[str, Any]] = []

    seed_sequence = np.random.SeedSequence(request.seed)
    weather_seed, pest_seed, transition_seed, output_seed = seed_sequence.spawn(4)
    weather_rng = np.random.default_rng(weather_seed)
    pest_rng = np.random.default_rng(pest_seed)
    transition_rng = np.random.default_rng(transition_seed)
    output_rng = np.random.default_rng(output_seed)

    beta_alpha = np.full(runs, 3 + context.base_pest * 10, dtype=float)
    beta_beta = np.full(runs, 17 + (1 - context.base_pest) * 10, dtype=float)
    baseline = request.farm.production.annual_production_tons

    for index, year in enumerate(years):
        events, severity, climate, _ = _sample_weather_year(
            runs, year, request.scenario, request.farm.location.latitude, weather_rng
        )
        sampled_pest = pest_rng.beta(beta_alpha, beta_beta)
        pest_reduction = SCENARIO_EFFECTS[request.intervention]["pest"]
        pest_probability = np.clip(
            0.48 * sampled_pest
            + 0.30 * context.base_pest
            + 0.22 * (climate["humidity"] / 100)
            + 0.13 * climate["stress"]
            - 0.35 * pest_reduction,
            0.005,
            0.95,
        )
        outbreak = pest_rng.random(runs) < pest_probability
        beta_alpha += outbreak
        beta_beta += ~outbreak
        outbreak_counts += outbreak.astype(np.int16)

        matrices = transition_matrices(request.intervention, climate["stress"], pest_probability, events)
        counts = stochastic_transition_batch(
            counts,
            matrices,
            transition_rng,
            _annual_replant_fraction(request, index),
        )
        values = _production_vector(
            request,
            counts,
            initial,
            context.suitability,
            climate,
            pest_probability,
            events,
            severity,
            output_rng,
            context.ml_corrections[request.intervention],
        )
        production[:, index] = values
        state_history[:, index, :] = counts

        for event in EVENTS:
            mask = events == event
            count = int(mask.sum())
            event_counter[str(event)] += count
            if event != "normal":
                event_counts[str(event)] += mask.astype(np.int16)
        annual_major_loss = (events != "normal") & (values < baseline * 0.75)
        major_loss_years += annual_major_loss.astype(np.int16)

        sample_events.append({
            "year": year,
            "event": str(events[0]),
            "severity": round(float(severity[0]), 3),
            "rainfall_mm": round(float(climate["rainfall"][0]), 1),
            "temperature_c": round(float(climate["temperature"][0]), 2),
            "climate_stress": round(float(climate["stress"][0]), 3),
            "pest_probability": round(float(pest_probability[0]), 3),
            "production_tons": round(float(values[0]), 3),
            "states": {state: int(counts[0, i]) for i, state in enumerate(STATES)},
        })

    yearly = []
    for index, year in enumerate(years):
        values = production[:, index]
        states = state_history[:, index, :]
        yearly.append({
            "year": year,
            "mean": round(float(np.mean(values)), 4),
            "median": round(float(np.median(values)), 4),
            "p05": round(float(np.quantile(values, 0.05)), 4),
            "p25": round(float(np.quantile(values, 0.25)), 4),
            "p75": round(float(np.quantile(values, 0.75)), 4),
            "p95": round(float(np.quantile(values, 0.95)), 4),
            "mean_states": {state: round(float(states[:, i].mean()), 2) for i, state in enumerate(STATES)},
        })

    final_values = production[:, -1]
    final_states = state_history[:, -1, :]
    final_total = np.maximum(1, final_states.sum(axis=1))
    healthy_recovering = (final_states[:, 1] + final_states[:, 5]) / final_total
    rehabilitation = (
        (final_values >= baseline * request.recovery_threshold_ratio)
        & (healthy_recovering >= 0.55)
    )
    severe_loss = (
        (final_values < baseline * request.severe_loss_threshold_ratio)
        | (final_states[:, 6] / final_total > 0.30)
    )
    major_weather_loss = major_loss_years > 0
    discount = np.array([1 / (1.03**i) for i in range(n_years)])
    discounted_output = (production * discount).sum(axis=1)
    normalized_output = float(np.mean(discounted_output) / max(1e-9, baseline * discount.sum()))
    burden_adjustment = 0.004 * request.farm.management.intervention_burden_score
    intervention_cost = INTERVENTION_COST[request.intervention] + burden_adjustment
    risk_penalty = 0.85 * float(severe_loss.mean())
    utility = normalized_output - intervention_cost - risk_penalty
    healthy_history = (state_history[:, :, 1] + state_history[:, :, 5]) / np.maximum(1, state_history.sum(axis=2))
    recovery_condition = (production >= baseline * request.recovery_threshold_ratio) & (healthy_history >= 0.55)
    recovery_years = np.full(runs, np.nan)
    window = min(3, n_years)
    for start_index in range(0, n_years - window + 1):
        sustained = recovery_condition[:, start_index:start_index + window].all(axis=1)
        newly_recovered = np.isnan(recovery_years) & sustained
        recovery_years[newly_recovered] = years[start_index]
    # A recovery year is reported only for paths that still satisfy the recovery
    # condition at the end of the selected horizon.
    recovery_years[~rehabilitation] = np.nan
    finite_recovery = recovery_years[~np.isnan(recovery_years)]

    uncertainty_candidates = {
        "drought occurrence": event_counts["drought"].astype(float),
        "extreme-rain occurrence": event_counts["extreme_rain"].astype(float),
        "heat-stress occurrence": event_counts["heat_stress"].astype(float),
        "typhoon exposure": event_counts["typhoon"].astype(float),
        "pest outbreaks": outbreak_counts.astype(float),
        "final dead-palm fraction": final_states[:, 6] / final_total,
    }
    correlations = {name: _safe_correlation(values, final_values) for name, values in uncertainty_candidates.items()}
    dominant_uncertainty = max(correlations, key=lambda name: abs(correlations[name]))

    rehab_probability = float(rehabilitation.mean())
    severe_probability = float(severe_loss.mean())
    weather_loss_probability = float(major_weather_loss.mean())
    standard_error = lambda p: math.sqrt(max(p * (1 - p), 0) / runs)

    warnings = [
        "Plausible simulated future, not an exact forecast.",
        "Agricultural model artifacts were trained on synthetic reference-based development data.",
    ]
    if context.fallback_models:
        warnings.append(f"Formula fallback was used for unavailable or incompatible models: {', '.join(context.fallback_models)}.")

    return {
        "intervention": request.intervention,
        "scenario": request.scenario,
        "start_year": request.start_year,
        "end_year": request.end_year,
        "runs": runs,
        "seed": request.seed,
        "baseline_production_tons": baseline,
        "recovery_threshold_ratio": request.recovery_threshold_ratio,
        "severe_loss_threshold_ratio": request.severe_loss_threshold_ratio,
        "suitability_score": round(context.suitability, 5),
        "initial_pest_posterior": round(context.base_pest, 5),
        "yearly": yearly,
        "summary": {
            "final_mean_tons": round(float(np.mean(final_values)), 4),
            "final_median_tons": round(float(np.median(final_values)), 4),
            "final_90_percent_interval": [
                round(float(np.quantile(final_values, 0.05)), 4),
                round(float(np.quantile(final_values, 0.95)), 4),
            ],
            "rehabilitation_probability": round(rehab_probability, 5),
            "severe_loss_probability": round(severe_probability, 5),
            "major_weather_loss_probability": round(weather_loss_probability, 5),
            "annualized_major_weather_loss_rate": round(float(major_loss_years.sum() / (runs * n_years)), 5),
            "mean_major_weather_loss_years": round(float(major_loss_years.mean()), 3),
            "median_recovery_year": int(np.median(finite_recovery)) if len(finite_recovery) else None,
            "expected_utility": round(float(utility), 6),
            "utility_components": {
                "normalized_discounted_output": round(normalized_output, 6),
                "intervention_burden": round(intervention_cost, 6),
                "severe_loss_penalty": round(risk_penalty, 6),
            },
            "monte_carlo_standard_errors": {
                "rehabilitation": round(standard_error(rehab_probability), 6),
                "severe_loss": round(standard_error(severe_probability), 6),
                "major_weather_loss": round(standard_error(weather_loss_probability), 6),
            },
            "dominant_uncertainty_source": dominant_uncertainty,
            "uncertainty_correlations": {name: round(value, 4) for name, value in correlations.items()},
        },
        "event_frequencies": {
            key: round(value / (runs * n_years), 5)
            for key, value in sorted(event_counter.items())
        },
        "sample_trajectory": sample_events,
        "model_versions": context.model_versions,
        "reference_state_assumptions": {
            "productive_equivalent_share": 0.68,
            "reference_stressed_share": 0.07,
            "reference_infested_share": 0.04,
            "reference_dead_share": 0.03,
        },
        "intervention_cost_assumptions": INTERVENTION_COST,
        "calculation_version": settings.calculation_version,
        "parameter_version": settings.parameter_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "data_source_type": "synthetic_reference_based",
        "warnings": warnings,
        "limitations": [
            "Transition and intervention parameters require calibration with verified longitudinal coconut-farm records.",
            "Long-term typhoon exposure is sampled probabilistically and does not predict exact storm dates.",
            "Within-farm differences are not inferred unless measured spatial inputs are supplied.",
            "Reference productive-palm and health shares are provisional development assumptions that require field calibration.",
        ],
    }
