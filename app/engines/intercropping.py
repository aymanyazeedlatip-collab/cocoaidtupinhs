from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.bayesian import repository as bayesian_repository
from app.core.errors import EngineExecutionError
from app.data_foundation import repository as data_repository
from app.domain.enums import ConfidenceLevel, EngineAvailability, EngineMaturity
from app.domain.intercropping import (
    IntercropAssessmentRequest,
    IntercropCandidateAssessment,
    IntercropCandidateSnapshot,
    IntercropEngineOutput,
    IntercropEngineSummary,
)
from app.domain.provenance import RunProvenance, VersionReference
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.engines.registry import engine_registry
from app.intercropping import repository
from app.intercropping.parameters import (
    CANOPY_LIGHT_ADAPTER_VERSION,
    INTERCROP_ENGINE_VERSION,
    INTERCROP_PARAMETER_VERSION,
    INTERCROP_REQUIREMENT_PROFILE_VERSION,
    PARAMETERS,
)
from app.intercropping.suitability import (
    aggregate_crop_profiles,
    annualized_rainfall,
    component,
    economic_potential,
    estimate_canopy_light,
    geometric_score,
    inverse_demand_score,
    planting_window,
    range_score,
    suitability_class,
    threshold_score,
    weather_temperature_estimate,
)
from app.production import repository as production_repository
from app.weather.assimilation import repository as weather_repository

INTERCROP_DATA_NOTICE = (
    "Phase 7 is a transparent evidence-scoring engine, not a supervised intercropping ML model. "
    "PCA brochure crop light bands and canopy transmission rows are source-backed. Non-light crop requirements, "
    "component weights, competition coefficients, and pest-conflict coefficients are versioned development assumptions "
    "pending PCA/expert review and field calibration. Cacao and coffee economics use sanitized historical gross revenue, "
    "not net profit or guaranteed future income."
)

INTERCROP_DESCRIPTOR = EngineDescriptor(
    engine_id="v3.intercropping",
    name="Spatial Intercropping Potential Engine",
    version=INTERCROP_ENGINE_VERSION,
    maturity=EngineMaturity.EXPERIMENTAL,
    availability=EngineAvailability.AVAILABLE,
    input_contract="IntercropAssessmentRequest",
    output_contract="IntercropEngineOutput",
    dependencies=[
        "v3.weather_assimilation", "v3.production", "v3.pest_inference",
        "canopy_light_registry", "intercrop_requirement_registry",
    ],
    limitations=[
        "Only light requirements and canopy transmission are directly supported by the uploaded PCA brochure",
        "Non-light numerical requirements require expert validation",
        "Pest conflict is conditional on a supplied Phase 6 assessment run",
        "Economic estimates are gross-revenue scenarios for cacao and coffee only",
        "No supervised intercropping model is claimed",
    ],
)


def _features(feature_set: dict) -> dict[str, float]:
    return {item["name"]: float(item["value"]) for item in feature_set["features"]}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class IntercroppingEngine(AnalyticalEngine[IntercropAssessmentRequest, IntercropEngineOutput]):
    descriptor = INTERCROP_DESCRIPTOR
    input_model = IntercropAssessmentRequest
    output_model = IntercropEngineOutput

    def __init__(self, *, database_path: Path | None = None):
        self.database_path = database_path

    def _run(self, payload: IntercropAssessmentRequest, context: EngineExecutionContext):
        forecast = production_repository.get_forecast(
            payload.production_forecast_id, database_path=self.database_path,
        )
        if not forecast:
            raise EngineExecutionError(
                "Production forecast not found",
                details={"production_forecast_id": str(payload.production_forecast_id)},
            )
        if forecast["farm_id"] != str(payload.farm_id):
            raise EngineExecutionError("Intercropping request farm_id does not match the production forecast")
        snapshot = production_repository.get_feature_snapshot(
            forecast["feature_snapshot_id"], database_path=self.database_path,
        )
        if not snapshot:
            raise EngineExecutionError("Production feature snapshot not found")
        feature_set = weather_repository.get_feature_set(
            snapshot["weather_feature_set_id"], database_path=self.database_path,
        )
        if not feature_set:
            raise EngineExecutionError("Weather feature set linked to production forecast not found")

        if payload.posterior_id:
            posterior = bayesian_repository.get_posterior(payload.posterior_id, database_path=self.database_path)
            if not posterior:
                raise EngineExecutionError("Bayesian posterior not found", details={"posterior_id": str(payload.posterior_id)})
            if posterior["farm_id"] != str(payload.farm_id):
                raise EngineExecutionError("Bayesian posterior farm_id does not match the intercropping request")
            if posterior["production_forecast_id"] != str(payload.production_forecast_id):
                raise EngineExecutionError("Bayesian posterior does not belong to the supplied production forecast")

        candidates = repository.load_candidates(payload.candidate_ids or None, database_path=self.database_path)
        if payload.candidate_ids:
            found = {item["id"] for item in candidates}
            missing = sorted(set(payload.candidate_ids) - found)
            if missing:
                raise EngineExecutionError(
                    "Unsupported or uninitialized intercrop candidate",
                    details={"missing": missing},
                )
        if not candidates:
            raise EngineExecutionError("Intercrop reference candidates are not initialized")

        canopy_rows = repository.load_canopy_parameters(database_path=self.database_path)
        if not canopy_rows:
            raise EngineExecutionError("PCA canopy-light parameters are not initialized")

        pest_probabilities: dict[str, float] = {}
        if payload.pest_assessment_run_id:
            pest_run = repository.load_pest_run(payload.pest_assessment_run_id, database_path=self.database_path)
            if not pest_run:
                raise EngineExecutionError(
                    "Pest assessment run not found",
                    details={"pest_assessment_run_id": str(payload.pest_assessment_run_id)},
                )
            if pest_run["farm_id"] != str(payload.farm_id):
                raise EngineExecutionError("Pest assessment run farm_id does not match the intercropping request")
            if pest_run["production_forecast_id"] != str(payload.production_forecast_id):
                raise EngineExecutionError("Pest assessment run does not belong to the supplied production forecast")
            pest_probabilities = {
                item["pest_profile_id"]: float(item["outbreak_probability"])
                for item in pest_run["assessments"]
            }

        features = _features(feature_set)
        annual_rain = annualized_rainfall(features)
        temperature = weather_temperature_estimate(features)
        solar = features.get("mean_solar_radiation_90d_mj_m2_day")
        dry_days = features.get("consecutive_dry_days", 0.0)
        economic_profiles = aggregate_crop_profiles(data_repository.intercrop_income_assessment(database_path=self.database_path))
        run_id = uuid4()
        assessments: list[IntercropCandidateAssessment] = []
        economic_used: set[str] = set()

        for cell in payload.cells:
            light = estimate_canopy_light(cell=cell, canopy_rows=canopy_rows, solar_radiation_mj_m2_day=solar)
            for candidate in candidates:
                weights = PARAMETERS["component_weights"]
                light_score = range_score(
                    light.transmitted_light_fraction,
                    float(candidate["min_light_fraction"]),
                    float(candidate["max_light_fraction"]),
                    tolerance_fraction=0.50,
                )
                light_hard = (
                    light.transmitted_light_fraction >= float(candidate["min_light_fraction"]) * PARAMETERS["hard_light_lower_ratio"]
                    and light.transmitted_light_fraction <= min(
                        1.0, float(candidate["max_light_fraction"]) * PARAMETERS["hard_light_upper_ratio"]
                    )
                )
                components = [
                    component(
                        "light", light_score, weights["light"],
                        f"Estimated understory light {light.transmitted_light_fraction:.3f}; candidate range "
                        f"{candidate['min_light_fraction']:.3f}–{candidate['max_light_fraction']:.3f}.",
                        hard_constraint_passed=light_hard,
                    ),
                    component(
                        "temperature", range_score(temperature, candidate["min_temperature_c"], candidate["max_temperature_c"]),
                        weights["temperature"],
                        f"Development temperature proxy {temperature:.2f} °C versus provisional range "
                        f"{candidate['min_temperature_c']:.1f}–{candidate['max_temperature_c']:.1f} °C.",
                    ),
                    component(
                        "rainfall_water",
                        0.60 * range_score(annual_rain, candidate["min_rainfall_mm_year"], candidate["max_rainfall_mm_year"])
                        + 0.40 * range_score(cell.soil_moisture_index, candidate["min_soil_moisture_index"], candidate["max_soil_moisture_index"]),
                        weights["rainfall_water"],
                        f"Annualized 90-day rainfall reference {annual_rain:.0f} mm/year and cell soil-moisture index "
                        f"{cell.soil_moisture_index:.2f}; {dry_days:.0f} consecutive dry days recorded.",
                    ),
                    component(
                        "soil_ph", range_score(cell.soil_ph, candidate["min_soil_ph"], candidate["max_soil_ph"]),
                        weights["soil_ph"],
                        f"Cell soil pH {cell.soil_ph:.2f} versus provisional range {candidate['min_soil_ph']:.1f}–{candidate['max_soil_ph']:.1f}.",
                    ),
                    component(
                        "drainage", threshold_score(cell.drainage_index, candidate["min_drainage_index"]),
                        weights["drainage"],
                        f"Drainage index {cell.drainage_index:.2f}; provisional minimum {candidate['min_drainage_index']:.2f}.",
                    ),
                    component(
                        "space", inverse_demand_score(cell.available_space_fraction, candidate["space_demand"]),
                        weights["space"],
                        f"Available-space fraction {cell.available_space_fraction:.2f}; crop space demand {candidate['space_demand']:.2f}.",
                    ),
                    component(
                        "nitrogen", inverse_demand_score(cell.nitrogen_index, candidate["nutrient_demand"]),
                        weights["nitrogen"],
                        f"Nitrogen index {cell.nitrogen_index:.2f}; provisional nutrient demand {candidate['nutrient_demand']:.2f}.",
                    ),
                    component(
                        "management", inverse_demand_score(cell.management_feasibility, candidate["management_demand"]),
                        weights["management"],
                        f"Management feasibility {cell.management_feasibility:.2f}; management demand {candidate['management_demand']:.2f}.",
                    ),
                    component(
                        "slope", max(0.0, 1.0 - cell.slope_degrees / PARAMETERS["hard_slope_degrees"]),
                        weights["slope"],
                        f"Cell slope {cell.slope_degrees:.1f}°; slopes above {PARAMETERS['hard_slope_degrees']:.0f}° are a Phase 7 hard constraint.",
                        hard_constraint_passed=cell.slope_degrees <= PARAMETERS["hard_slope_degrees"],
                    ),
                ]
                water_shortage = max(0.0, candidate["water_demand"] - cell.soil_moisture_index)
                root_pressure = candidate["root_competition"] * (1.0 - cell.available_space_fraction)
                nutrient_pressure = candidate["nutrient_demand"] * (1.0 - cell.nitrogen_index)
                coconut_competition = _clamp(0.45 * water_shortage + 0.35 * root_pressure + 0.20 * nutrient_pressure)

                conflicts = [pest_probabilities[item] for item in candidate["pest_conflict_ids"] if item in pest_probabilities]
                benefits = [pest_probabilities[item] for item in candidate["beneficial_pest_ids"] if item in pest_probabilities]
                general_pressure = max(pest_probabilities.values(), default=0.0)
                pest_conflict = _clamp(
                    (sum(conflicts) / len(conflicts) if conflicts else 0.0)
                    + 0.15 * general_pressure
                    - 0.25 * (sum(benefits) / len(benefits) if benefits else 0.0)
                )

                base = geometric_score(components)
                final = 100.0 * base * (1.0 - PARAMETERS["competition_penalty_weight"] * coconut_competition)
                final *= 1.0 - PARAMETERS["pest_penalty_weight"] * pest_conflict
                hard_pass = all(item.hard_constraint_passed for item in components)
                if not hard_pass:
                    final = min(final, PARAMETERS["hard_constraint_score_cap"])
                final = max(0.0, min(100.0, final))
                limiting = [
                    item.factor for item in sorted(components, key=lambda value: value.score)[:3]
                    if item.score < 0.75
                ]
                start, end = planting_window(payload.assessed_at.date(), candidate["planting_months"])
                economics = economic_potential(
                    candidate_id=candidate["economic_profile_crop"] or "",
                    area_hectares=cell.area_hectares,
                    suitability_score_value=final,
                    crop_profiles=economic_profiles,
                    enabled=payload.include_economic_potential,
                )
                if economics.status == "available":
                    economic_used.add(candidate["economic_profile_crop"])
                notes = [
                    "PCA source directly supports the candidate light band and canopy transmission rows.",
                    "Temperature is a bounded development proxy because the Phase 3 feature set does not yet retain mean temperature.",
                    candidate["requirement_notes"],
                ]
                if not pest_probabilities:
                    notes.append("No Phase 6 pest assessment run was supplied; pest-conflict risk remains unconditioned at zero.")
                confidence = ConfidenceLevel.MODERATE if light.confidence == ConfidenceLevel.HIGH else ConfidenceLevel.LOW
                recommended_layout = (
                    f"Use only the assessed {cell.area_hectares:.3f}-ha cell area, preserve coconut access and sanitation lanes, "
                    f"and begin with a monitored pilot occupying no more than {min(0.75, cell.available_space_fraction):.0%} of available understory space. "
                    "Reassess soil moisture, canopy closure, coconut production, and pest observations before expansion."
                )
                provenance = RunProvenance(
                    farm_data_version=payload.farm_data_version,
                    weather_run_id=feature_set["weather_run_id"],
                    model_versions=[VersionReference(component="intercropping_engine", version=INTERCROP_ENGINE_VERSION)],
                    parameter_versions=[
                        VersionReference(component="intercrop_scoring_parameters", version=INTERCROP_PARAMETER_VERSION),
                        VersionReference(component="intercrop_requirement_profiles", version=INTERCROP_REQUIREMENT_PROFILE_VERSION),
                    ],
                    source_versions=[VersionReference(component="pca_canopy_light_catalog", version="phase2-catalog-1.0.0")],
                    feature_adapter_version=CANOPY_LIGHT_ADAPTER_VERSION,
                    warnings=notes,
                    limitations=[INTERCROP_DATA_NOTICE],
                )
                assessments.append(IntercropCandidateAssessment(
                    run_id=run_id,
                    farm_id=payload.farm_id,
                    cell_id=cell.cell_id,
                    cell_label=cell.label,
                    production_forecast_id=payload.production_forecast_id,
                    posterior_id=payload.posterior_id,
                    pest_assessment_run_id=payload.pest_assessment_run_id,
                    assessed_at=payload.assessed_at,
                    candidate=IntercropCandidateSnapshot(
                        candidate_id=candidate["id"], common_name=candidate["common_name"],
                        scientific_name=candidate["scientific_name"], light_group=candidate["light_group"],
                        minimum_light_fraction=candidate["min_light_fraction"],
                        maximum_light_fraction=candidate["max_light_fraction"],
                        reference_confidence=candidate["confidence"],
                        requirement_profile_version=candidate["profile_version"],
                        requirement_basis=candidate["basis"], source_document_id=candidate["source_document_id"],
                        source_page=candidate["source_page"],
                    ),
                    suitability_score=final,
                    suitability_class=suitability_class(final),
                    hard_constraint_passed=hard_pass,
                    components=components,
                    limiting_factors=limiting,
                    canopy_light=light,
                    coconut_competition_risk=coconut_competition,
                    pest_conflict_risk=pest_conflict,
                    planting_window_start=start,
                    planting_window_end=end,
                    recommended_layout=recommended_layout,
                    economic_potential=economics,
                    confidence=confidence,
                    data_quality_notes=notes,
                    provenance=provenance,
                ))

        assessments.sort(key=lambda item: (str(item.cell_id), -item.suitability_score, item.candidate.common_name))
        best: dict[str, str] = {}
        for item in assessments:
            best.setdefault(str(item.cell_id), item.candidate.candidate_id)
        warnings = [
            "This is an evidence-based scoring engine, not a validated supervised ML model.",
            "Non-light crop requirement values require PCA/expert review before operational deployment.",
        ]
        if not pest_probabilities:
            warnings.append("No Phase 6 pest run was supplied, so candidate-specific pest conflicts were not conditioned on current pest probabilities.")
        output = IntercropEngineOutput(
            run_id=run_id,
            assessments=assessments,
            summary=IntercropEngineSummary(
                assessed_cell_count=len(payload.cells),
                assessed_candidate_count=len(candidates),
                total_assessment_count=len(assessments),
                high_or_very_high_count=sum(item.suitability_class in {"high", "very_high"} for item in assessments),
                best_candidate_by_cell=best,
                economic_profiles_used=sorted(economic_used),
            ),
            parameter_version=INTERCROP_PARAMETER_VERSION,
            requirement_profile_version=INTERCROP_REQUIREMENT_PROFILE_VERSION,
            weather_feature_set_id=feature_set["id"],
            weather_run_id=feature_set["weather_run_id"],
            data_notice=INTERCROP_DATA_NOTICE,
            warnings=warnings,
        )
        repository.save_output(
            output,
            request_payload={
                "farm_id": str(payload.farm_id),
                "production_forecast_id": str(payload.production_forecast_id),
                "posterior_id": str(payload.posterior_id) if payload.posterior_id else None,
                "pest_assessment_run_id": str(payload.pest_assessment_run_id) if payload.pest_assessment_run_id else None,
                "assessed_at": payload.assessed_at.isoformat(),
                "candidate_ids": [item["id"] for item in candidates],
                "cells": [item.model_dump(mode="json") for item in payload.cells],
            },
            database_path=self.database_path,
        )
        return output, warnings


intercropping_engine = IntercroppingEngine()
engine_registry.register(intercropping_engine)

__all__ = [
    "INTERCROP_DATA_NOTICE", "INTERCROP_DESCRIPTOR", "IntercroppingEngine", "intercropping_engine",
]
