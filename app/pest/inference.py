from __future__ import annotations

import math
from datetime import timedelta
from typing import Any
from uuid import UUID

from app.domain.enums import ConfidenceLevel, EvidenceStatus
from app.domain.pest import (
    NearbyConfirmedPestCase,
    PestAssessmentRequest,
    PestEvidenceContribution,
    PestFarmContext,
    PestManagementAction,
    PestProfileAssessment,
    PestProfileSnapshot,
)
from app.domain.provenance import RunProvenance, VersionReference
from app.domain.units import UnitCode
from app.pest.parameters import (
    PARAMETERS,
    PEST_PARAMETER_VERSION,
    evidence_reliability,
    likelihood_ratio,
    spatial_kernel,
)


def _logit(probability: float) -> float:
    p = min(1 - 1e-9, max(1e-9, float(probability)))
    return math.log(p / (1 - p))


def _sigmoid(value: float) -> float:
    clipped = min(30.0, max(-30.0, float(value)))
    return 1.0 / (1.0 + math.exp(-clipped))


def _risk_class(probability: float) -> str:
    thresholds = PARAMETERS["risk_thresholds"]
    if probability >= thresholds["critical"]:
        return "critical"
    if probability >= thresholds["high"]:
        return "high"
    if probability >= thresholds["moderate"]:
        return "moderate"
    return "low"


def _weather_values(feature_set: dict[str, Any], production_snapshot: dict[str, Any]) -> dict[str, float]:
    values = {str(item["name"]): float(item["value"]) for item in feature_set.get("features", [])}
    legacy = production_snapshot.get("features", {})
    values["mean_temperature_c"] = float(legacy.get("mean_temperature_c", 0.0))
    values["relative_humidity_percent"] = float(legacy.get("relative_humidity_percent", 0.0))
    return values


def _rule_match(factor_code: str, context: PestFarmContext, weather: dict[str, float], nearby: bool) -> bool:
    symptoms = set(context.symptom_codes)
    mapping = {
        "relative_humidity_94_100": 94.0 <= weather.get("relative_humidity_percent", -1) <= 100.0,
        "temperature_at_or_below_24c": weather.get("mean_temperature_c", 999) <= 24.0,
        "young_palms_under_20": bool(context.young_palms) or (
            context.mean_palm_age_years is not None and context.mean_palm_age_years < 20
        ),
        "waterlogging_or_poor_drainage": context.waterlogging or context.drainage_quality < 0.35,
        "spear_leaf_wilting": "spear_leaf_wilting" in symptoms,
        "young_palms": context.young_palms > 0,
        "poor_maintenance": context.maintenance_quality < 0.40,
        "dry_conditions": weather.get("consecutive_dry_days", 0.0) >= 7.0,
        "beneficial_organisms_present": context.natural_enemies_present,
        "breeding_material": context.decaying_organic_breeding_material,
        "crown_damage": "crown_or_spear_damage" in symptoms,
        "fresh_wounds": context.fresh_palm_wounds,
        "storm_damage": context.storm_damage,
        "internal_feeding_symptoms": "internal_feeding_or_boring" in symptoms,
        "confirmed_nearby_case": nearby,
        "scale_colonies": "scale_colonies_on_leaflets" in symptoms,
        "natural_enemies": context.natural_enemies_present,
    }
    return bool(mapping.get(factor_code, False))


def _exposed_palms(pest_id: str, context: PestFarmContext) -> int:
    if pest_id in {"bud-nut-rot", "coconut-leaf-beetle"}:
        vulnerable = context.young_palms + context.stressed_palms + context.infested_or_diseased_palms
    elif pest_id == "rhinoceros-beetle":
        vulnerable = context.young_palms + context.stressed_palms + context.infested_or_diseased_palms
    elif pest_id == "asiatic-palm-weevil":
        vulnerable = context.total_palms if context.fresh_palm_wounds or context.storm_damage else (
            context.stressed_palms + context.infested_or_diseased_palms
        )
    else:
        vulnerable = context.total_palms
    return min(context.total_palms, max(0, vulnerable))


def _severity(context: PestFarmContext, diagnostic_matches: int, exposed: int) -> float:
    settings = PARAMETERS["severity"]
    vulnerable_fraction = exposed / max(1, context.total_palms)
    current_fraction = context.infested_or_diseased_palms / max(1, context.total_palms)
    severity = (
        settings["minimum"]
        + settings["diagnostic_increment"] * min(2, diagnostic_matches)
        + settings["vulnerability_weight"] * vulnerable_fraction
        + settings["current_infestation_weight"] * current_fraction
    )
    return min(settings["maximum"], max(settings["minimum"], severity))


def _spatial_pressure(pest_id: str, cases: list[NearbyConfirmedPestCase]) -> tuple[float, int]:
    remaining = 1.0
    count = 0
    for case in cases:
        if case.pest_profile_id != pest_id:
            continue
        reliability = evidence_reliability(case.evidence_status.value)
        if reliability <= 0:
            continue
        contribution = min(1.0, case.outbreak_probability * reliability * spatial_kernel(case.distance_m))
        remaining *= 1.0 - contribution
        count += 1
    return min(1.0, max(0.0, 1.0 - remaining)), count


def evaluate_pest_profile(
    *,
    request: PestAssessmentRequest,
    run_id: UUID,
    profile: dict[str, Any],
    rules: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    feature_set: dict[str, Any],
    production_snapshot: dict[str, Any],
    baseline_production_tonnes: float,
    weather_run_id: UUID,
) -> PestProfileAssessment:
    pest_id = str(profile["id"])
    weather = _weather_values(feature_set, production_snapshot)
    spatial_pressure, nearby_count = _spatial_pressure(pest_id, request.nearby_confirmed_cases)
    contributions: list[PestEvidenceContribution] = []
    sequence = 1
    prior = float(PARAMETERS["baseline_inspection_prior"])
    log_odds = _logit(prior)
    contributions.append(PestEvidenceContribution(
        sequence=sequence,
        factor_code="baseline_inspection_prior",
        source_kind="baseline_prior",
        direction="increases_risk",
        matched=True,
        likelihood_ratio=1.0,
        log_odds_delta=0.0,
        confidence=ConfidenceLevel.LOW,
        explanation="Uniform development inspection prior; it is not a measured local prevalence estimate.",
    ))
    sequence += 1
    diagnostic_matches = 0
    rule_map = {str(rule["factor_code"]): rule for rule in rules}
    nearby = nearby_count > 0

    for rule in rules:
        matched = _rule_match(str(rule["factor_code"]), request.context, weather, nearby)
        confidence = ConfidenceLevel(str(rule["confidence"]))
        lr = float(rule.get("likelihood_ratio") or likelihood_ratio(str(rule["direction"]), confidence.value))
        delta = math.log(lr) if matched else 0.0
        if matched:
            log_odds += delta
            if rule["direction"] == "diagnostic_signal":
                diagnostic_matches += 1
        source_kind = "weather_feature" if rule["factor_code"] in {
            "relative_humidity_94_100", "temperature_at_or_below_24c", "dry_conditions"
        } else ("symptom" if rule["direction"] == "diagnostic_signal" else "farm_context")
        contributions.append(PestEvidenceContribution(
            sequence=sequence,
            factor_code=str(rule["factor_code"]),
            source_kind=source_kind,
            direction=str(rule["direction"]),
            matched=matched,
            likelihood_ratio=lr,
            log_odds_delta=delta,
            confidence=confidence,
            explanation=str(rule["explanation"]),
            source_document_id=str(profile["source_document_id"]),
            source_page=int(rule["source_page"]),
        ))
        sequence += 1

    if spatial_pressure > 0:
        max_lr = float(PARAMETERS["spatial"]["maximum_likelihood_ratio"])
        lr = 1.0 + spatial_pressure * (max_lr - 1.0)
        delta = math.log(lr)
        log_odds += delta
        contributions.append(PestEvidenceContribution(
            sequence=sequence,
            factor_code="distance_decayed_nearby_confirmed_cases",
            source_kind="spatial_case",
            direction="increases_risk",
            matched=True,
            likelihood_ratio=lr,
            log_odds_delta=delta,
            confidence=ConfidenceLevel.MODERATE,
            evidence_status=EvidenceStatus.FIELD_CONFIRMED,
            explanation=f"Combined distance-decayed pressure from {nearby_count} nearby confirmed case(s).",
        ))
        sequence += 1

    for observation in observations:
        if observation["pest_profile_id"] != pest_id:
            continue
        status = EvidenceStatus(observation["evidence_status"])
        reliability = evidence_reliability(status.value)
        factor_code = str(observation["factor_code"])
        source_rule = rule_map.get(factor_code)
        if observation.get("prevalence_fraction") is not None:
            raw_lr = 1.0 + float(observation["prevalence_fraction"]) * (
                float(PARAMETERS["observation_prevalence_max_likelihood_ratio"]) - 1.0
            )
            direction = "diagnostic_signal"
            confidence = ConfidenceLevel.HIGH
            explanation = "Observed pest prevalence supplied as explicit field evidence."
        elif source_rule:
            direction = str(source_rule["direction"])
            confidence = ConfidenceLevel(str(source_rule["confidence"]))
            raw_lr = float(source_rule.get("likelihood_ratio") or likelihood_ratio(direction, confidence.value))
            explanation = str(source_rule["explanation"])
        else:
            direction = "diagnostic_signal"
            confidence = ConfidenceLevel.MODERATE
            raw_lr = likelihood_ratio(direction, confidence.value)
            explanation = "Additional pest observation not mapped to a PCA factor code; retained with moderate development weight."
        effective_lr = raw_lr ** reliability if reliability > 0 else 1.0
        delta = math.log(effective_lr) if reliability > 0 else 0.0
        if reliability > 0:
            log_odds += delta
            if direction == "diagnostic_signal":
                diagnostic_matches += 1
        contributions.append(PestEvidenceContribution(
            sequence=sequence,
            factor_code=factor_code,
            source_kind="field_observation",
            direction=direction,
            matched=True,
            likelihood_ratio=effective_lr,
            log_odds_delta=delta,
            confidence=confidence,
            evidence_status=status,
            explanation=(
                explanation if reliability > 0
                else "Predicted or suspected evidence was stored for traceability but did not alter probability."
            ),
            source_document_id=str(profile["source_document_id"]) if source_rule else None,
            source_page=int(source_rule["source_page"]) if source_rule else None,
        ))
        sequence += 1

    probability = _sigmoid(log_odds)
    risk_class = _risk_class(probability)
    exposed = _exposed_palms(pest_id, request.context)
    severity = _severity(request.context, diagnostic_matches, exposed)
    conditional_loss = baseline_production_tonnes * (exposed / request.context.total_palms) * severity
    expected_loss = probability * conditional_loss
    inspection_date = request.assessed_at + timedelta(days=int(PARAMETERS["inspection_days"][risk_class]))
    quarantine = None
    if pest_id == "coconut-scale-insect" and any(
        item.factor_code in {"scale_colonies", "confirmed_nearby_case"} and item.matched
        for item in contributions
    ):
        quarantine = (
            "Possible coconut scale insect evidence is present. Do not move suspect planting material or infested leaves; "
            "obtain PCA/LGU confirmation and follow the current quarantine protocol if infestation is confirmed."
        )

    management = [PestManagementAction(
        sequence=index,
        action_type=str(action["action_type"]),
        timing=action.get("timing"),
        action_text=str(action["action_text"]),
        safety_notes=action.get("safety_notes"),
        source_document_id=str(profile["source_document_id"]),
        source_page=int(action["source_page"]),
    ) for index, action in enumerate(actions, start=1)]
    symptoms = [str(rule["condition"].get("symptom")) for rule in rules if rule["condition"].get("symptom")]
    provenance = RunProvenance(
        run_id=run_id,
        farm_data_version=request.farm_data_version,
        weather_run_id=weather_run_id,
        parameter_versions=[VersionReference(component="pest_inference_parameters", version=PEST_PARAMETER_VERSION)],
        source_versions=[VersionReference(component=str(profile["source_document_id"]), version=f"page-{profile['source_page']}")],
        warnings=[
            "Likelihood ratios and severity coefficients are development assumptions pending field calibration."
        ],
        limitations=[
            "This assessment indicates outbreak plausibility and inspection priority, not laboratory diagnosis.",
            "Expected losses for multiple pests overlap and should not be added as independent realized losses.",
        ],
    )
    return PestProfileAssessment(
        run_id=run_id,
        farm_id=request.farm_id,
        cell_id=request.cell_id,
        production_forecast_id=request.production_forecast_id,
        posterior_id=request.posterior_id,
        assessed_at=request.assessed_at,
        profile=PestProfileSnapshot(
            pest_profile_id=pest_id,
            common_name=str(profile["common_name"]),
            scientific_name=profile.get("scientific_name"),
            profile_type=str(profile["profile_type"]),
            reference_confidence=ConfidenceLevel(str(profile["confidence"])),
            source_document_id=str(profile["source_document_id"]),
            source_page=int(profile["source_page"]),
            notes=profile.get("notes"),
        ),
        outbreak_probability=probability,
        risk_class=risk_class,
        severity_if_outbreak=severity,
        exposed_palms=exposed,
        conditional_loss=conditional_loss,
        expected_loss=expected_loss,
        loss_unit=UnitCode.TONNE,
        spatial_pressure=spatial_pressure,
        evidence_contributions=contributions,
        symptoms_to_inspect=list(dict.fromkeys(symptoms)),
        management_actions=management,
        recommended_inspection_at=inspection_date,
        quarantine_warning=quarantine,
        provenance=provenance,
    )


__all__ = ["PEST_PARAMETER_VERSION", "evaluate_pest_profile"]
