from __future__ import annotations

from app.schemas.analysis import ScenarioComparisonRequest, SimulationRequest
from app.simulation.engine import (
    INTERVENTION_COST,
    INTERVENTIONS,
    prepare_simulation_context,
    run_simulation,
)


def compare_scenarios(request: ScenarioComparisonRequest, context=None) -> dict:
    context = context or prepare_simulation_context(request.farm)
    simulations: dict[str, dict] = {}
    ranking = []
    for intervention in INTERVENTIONS:
        simulation = run_simulation(
            SimulationRequest(
                farm=request.farm,
                start_year=request.start_year,
                end_year=request.end_year,
                scenario=request.scenario,
                intervention=intervention,
                runs=request.runs,
                seed=request.seed,
                recovery_threshold_ratio=request.recovery_threshold_ratio,
                severe_loss_threshold_ratio=request.severe_loss_threshold_ratio,
            ),
            context=context,
        )
        simulations[intervention] = simulation
        summary = simulation["summary"]
        ranking.append({
            "intervention": intervention,
            "expected_utility": summary["expected_utility"],
            "final_median_tons": summary["final_median_tons"],
            "final_90_percent_interval": summary["final_90_percent_interval"],
            "rehabilitation_probability": summary["rehabilitation_probability"],
            "severe_loss_probability": summary["severe_loss_probability"],
            "major_weather_loss_probability": summary["major_weather_loss_probability"],
            "intervention_burden": summary["utility_components"]["intervention_burden"],
            "dominant_uncertainty_source": summary["dominant_uncertainty_source"],
            "yearly_median": [row["median"] for row in simulation["yearly"]],
            "years": [row["year"] for row in simulation["yearly"]],
        })

    ranking.sort(key=lambda item: item["expected_utility"], reverse=True)
    for rank, result in enumerate(ranking, start=1):
        result["rank"] = rank
    best = ranking[0]
    second = ranking[1]
    utility_gap = best["expected_utility"] - second["expected_utility"]
    confidence = "High" if utility_gap >= 0.08 else "Moderate" if utility_gap >= 0.03 else "Low"

    return {
        "recommended_intervention": best["intervention"],
        "recommended_simulation": simulations[best["intervention"]],
        "recommendation_confidence": confidence,
        "utility_gap_to_second": round(float(utility_gap), 6),
        "recommendation_explanation": (
            f"{best['intervention'].replace('_', ' ').title()} has the highest risk-adjusted expected utility "
            f"under the selected development parameters. The utility lead over the second-ranked option is "
            f"{utility_gap:.3f}, giving a {confidence.lower()} demonstration confidence classification."
        ),
        "ranking": ranking,
        "scenario": request.scenario,
        "runs_per_intervention": request.runs,
        "seed": request.seed,
        "recovery_threshold_ratio": request.recovery_threshold_ratio,
        "severe_loss_threshold_ratio": request.severe_loss_threshold_ratio,
        "data_source_type": "synthetic_reference_based",
        "warning": "The ranking is a research demonstration and is not an official farm-management prescription.",
        "limitations": [
            "Utility costs are normalized burden assumptions rather than verified farm budgets.",
            "The same random seed is used across interventions to improve scenario comparability.",
        ],
    }
