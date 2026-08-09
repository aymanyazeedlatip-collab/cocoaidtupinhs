from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.climate.projections import climate_projection
from app.core.config import settings
from app.data.official_production import public_profile
from app.gis.analysis import farm_assessment, rehabilitation_grid
from app.math.bayes import evaluate_pest_risk
from app.math.suitability import suitability_index
from app.models.registry import model_metadata, predict
from app.schemas.analysis import (
    ClimateProjectionRequest,
    FullAnalysisRequest,
    PestRiskRequest,
    ScenarioComparisonRequest,
    SuitabilityRequest,
)
from app.simulation.compare import compare_scenarios
from app.simulation.engine import prepare_simulation_context
from app.storage.database import save_analysis

DATA_NOTICE = (
    "Official PSA provincial coconut-production statistics are used where available. "
    "Unavailable periods, farm-scale conditions, and future outcomes are model-estimated and require field validation."
)


def _pest_row(request: PestRiskRequest) -> dict[str, Any]:
    s = request.symptoms
    return {
        "annual_rainfall_mm": request.rainfall_mm_month * 12,
        "mean_temperature_c": 27.0,
        "relative_humidity_percent": request.humidity_percent,
        "average_tree_age": request.average_tree_age,
        "yellowing": int(s.yellowing),
        "crown_decline": int(s.crown_decline),
        "frond_cuts": int(s.frond_cuts),
        "visible_scale_insects": int(s.visible_scale_insects),
        "rhinoceros_beetle_damage": int(s.rhinoceros_beetle_damage),
        "premature_nut_fall": int(s.premature_nut_fall),
        "nearby_reports": int(s.nearby_reports),
        "symptom_severity": s.severity,
        "pest_control": 0,
    }


def pest_assessment(request: PestRiskRequest) -> dict:
    ml = predict("pest", _pest_row(request))
    result = evaluate_pest_risk(request, ml)
    result.update({
        "model_version": model_metadata("pest")["pest"]["version"],
        "data_source_type": "development_model_estimate",
        "warning": DATA_NOTICE,
    })
    return result


def _suitability_row(request: SuitabilityRequest) -> dict[str, Any]:
    st = request.soil_terrain
    return {
        "annual_rainfall_mm": request.annual_rainfall_mm,
        "mean_temperature_c": request.mean_temperature_c,
        "relative_humidity_percent": request.humidity_percent,
        "elevation_m": st.elevation_m,
        "slope_degrees": st.slope_degrees,
        "soil_ph": st.soil_ph,
        "nitrogen_index": st.nitrogen_index,
        "phosphorus_index": st.phosphorus_index,
        "potassium_index": st.potassium_index,
        "drainage_index": st.drainage_index,
        "drought_exposure": request.drought_exposure,
        "typhoon_exposure": request.climate_stress,
    }


def suitability_assessment(request: SuitabilityRequest) -> dict:
    ml = predict("suitability", _suitability_row(request))
    result = suitability_index(request, ml)
    result.update({
        "model_version": model_metadata("suitability")["suitability"]["version"],
        "data_source_type": "development_model_estimate",
        "development_warning": DATA_NOTICE,
    })
    return result


def full_analysis(request: FullAnalysisRequest) -> dict:
    farm = request.farm
    context = prepare_simulation_context(farm)
    farm_summary = farm_assessment(farm)
    official_reference = public_profile(farm.location.province, farm.location.region)

    pest_request = PestRiskRequest(
        prior_probability=0.15,
        symptoms=farm.symptoms,
        humidity_percent=78,
        rainfall_mm_month=185,
        average_tree_age=farm.trees.average_age_years,
    )
    pest = evaluate_pest_risk(pest_request, context.pest_ml_probability)
    pest.update({
        "model_version": context.model_versions.get("pest", "formula-fallback-1.0"),
        "data_source_type": "development_model_estimate",
        "warning": DATA_NOTICE,
    })

    suitability_request = SuitabilityRequest(soil_terrain=farm.soil_terrain)
    suitability = suitability_index(suitability_request, context.suitability_ml_score)
    suitability.update({
        "model_version": context.model_versions.get("suitability", "formula-fallback-1.0"),
        "data_source_type": "development_model_estimate",
        "development_warning": DATA_NOTICE,
    })

    climate = climate_projection(ClimateProjectionRequest(
        latitude=farm.location.latitude,
        longitude=farm.location.longitude,
        scenario=request.scenario,
        period=request.period,
    ))
    comparison = compare_scenarios(
        ScenarioComparisonRequest(
            farm=farm,
            start_year=settings.default_start_year,
            end_year=request.end_year,
            scenario=request.scenario,
            runs=min(request.runs, 2000),
            seed=request.seed,
            recovery_threshold_ratio=request.recovery_threshold_ratio,
            severe_loss_threshold_ratio=request.severe_loss_threshold_ratio,
        ),
        context=context,
    )
    rehab_map = rehabilitation_grid(farm)
    top_sim = comparison["recommended_simulation"]
    result = {
        "farm_assessment": farm_summary,
        "pest_risk": pest,
        "land_suitability": suitability,
        "climate_projection": climate,
        "scenario_comparison": comparison,
        "recommended_simulation": top_sim,
        "rehabilitation_map": rehab_map,
        "official_production_reference": official_reference,
        "overview": {
            "farm_name": farm.name,
            "current_production_tons": farm.production.annual_production_tons,
            "pest_risk_probability": pest["posterior_probability"],
            "land_suitability_percentage": suitability["percentage"],
            "climate_scenario": request.scenario,
            "projected_end_year": request.end_year,
            "projected_end_median_tons": top_sim["summary"]["final_median_tons"],
            "rehabilitation_probability": top_sim["summary"]["rehabilitation_probability"],
            "severe_loss_probability": top_sim["summary"]["severe_loss_probability"],
            "recommended_intervention": comparison["recommended_intervention"],
            "recommendation_confidence": comparison["recommendation_confidence"],
        },
        "scientific_warning": DATA_NOTICE,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    actual_runs = min(request.runs, 2000)
    metadata = {
        "calculation_version": settings.calculation_version,
        "model_versions": context.model_versions,
        "parameter_version": settings.parameter_version,
        "data_source_type": "mixed_official_psa_and_model_estimates",
        "random_seed": request.seed,
        "simulation_count_per_intervention": actual_runs,
        "total_simulated_trajectories": actual_runs * len(comparison["ranking"]),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "valid_period": f"{settings.default_start_year}-{request.end_year}; climate period {request.period}",
        "recovery_threshold_ratio": request.recovery_threshold_ratio,
        "severe_loss_threshold_ratio": request.severe_loss_threshold_ratio,
        "warnings": [DATA_NOTICE],
        "limitations": [
            "The PSA dataset supplies provincial production totals, not measurements for the individual farm.",
            "Laboratory soil measurements and calibrated local pest likelihood ratios are not bundled.",
            "Long-term climate values are scenario-based projections, not exact future observations.",
            "The baseline current-condition grid is uniform unless measured within-farm layers are supplied; event-linked maps add model-estimated hazard footprints and still require field verification.",
        ],
    }
    analysis_id = save_analysis(request.model_dump(mode="json"), result, metadata)
    result["analysis_id"] = analysis_id
    result["metadata"] = metadata
    return result
