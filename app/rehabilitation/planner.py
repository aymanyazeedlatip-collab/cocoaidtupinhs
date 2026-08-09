from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from app.domain.enums import ConfidenceLevel, EvidenceStatus, RehabilitationActionType, RehabilitationTiming
from app.domain.rehabilitation import (
    CostEstimate,
    RehabilitationAction,
    RehabilitationCellContext,
    RehabilitationScenarioResult,
    RehabilitationTrigger,
    ScenarioType,
)
from app.domain.units import UnitCode
from app.rehabilitation.parameters import PARAMETERS, REHABILITATION_COST_CATALOG_VERSION


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def cost_estimate(action_type: RehabilitationActionType, area_hectares: float) -> CostEstimate:
    row = PARAMETERS["cost_catalog"][action_type.value]
    materials = row["materials_per_ha"] * area_hectares
    labor_days = row["labor_days_per_ha"] * area_hectares
    labor = labor_days * PARAMETERS["labor_day_rate_php"]
    other = row["other_per_ha"] * area_hectares
    return CostEstimate(
        materials_php=round(materials, 2),
        labor_php=round(labor, 2),
        other_php=round(other, 2),
        total_php=round(materials + labor + other, 2),
        labor_person_days=round(labor_days, 2),
        basis=(
            f"{REHABILITATION_COST_CATALOG_VERSION}; per-hectare development assumption scaled to "
            f"{area_hectares:.3f} ha at PHP {PARAMETERS['labor_day_rate_php']:.0f}/person-day."
        ),
    )


def _trigger(code: str, source: str, severity: float, description: str, *,
             status: EvidenceStatus | None = None, confirmed: bool = False,
             evidence_ids: list[UUID] | None = None) -> RehabilitationTrigger:
    return RehabilitationTrigger(
        trigger_code=code,
        source=source,
        severity=clamp(severity),
        evidence_status=status,
        evidence_ids=evidence_ids or [],
        description=description,
        confirmed_damage=confirmed,
    )


def detect_cell_triggers(
    cell: RehabilitationCellContext,
    *,
    pest_probability: float,
    pest_confirmed: bool,
    pest_evidence_ids: list[UUID],
    production_decline_probability: float,
    best_intercrop_score: float | None,
) -> list[RehabilitationTrigger]:
    t = PARAMETERS["trigger_thresholds"]
    total = max(cell.total_palms, 1)
    dead = cell.dead_palms / total
    aging = cell.aging_palms / total
    stressed = cell.stressed_palms / total
    infested = cell.infested_or_diseased_palms / total
    triggers: list[RehabilitationTrigger] = []
    if dead >= t["dead_fraction_partial"]:
        triggers.append(_trigger(
            "dead_or_nonproductive_palms", "farm_context", dead,
            f"{cell.dead_palms} of {cell.total_palms} planting positions are recorded dead.",
            status=EvidenceStatus.FIELD_CONFIRMED, confirmed=True,
        ))
    if aging >= t["aging_fraction"]:
        triggers.append(_trigger(
            "excessive_aging_share", "farm_context", aging,
            f"Aging palms represent {aging:.1%} of the cell inventory.",
            status=EvidenceStatus.FARMER_REPORTED, confirmed=True,
        ))
    if stressed >= t["stressed_fraction"]:
        triggers.append(_trigger(
            "environmental_stress", "farm_context", stressed,
            f"Stressed palms represent {stressed:.1%} of the cell inventory.",
            status=EvidenceStatus.FARMER_REPORTED, confirmed=True,
        ))
    if infested >= t["infested_fraction"]:
        triggers.append(_trigger(
            "recorded_infested_share", "farm_context", infested,
            f"Infested or diseased palms represent {infested:.1%} of the cell inventory.",
            status=EvidenceStatus.FARMER_REPORTED, confirmed=True,
        ))
    if cell.drainage_index < t["low_drainage"]:
        triggers.append(_trigger(
            "poor_drainage", "farm_context", 1.0 - cell.drainage_index,
            f"Drainage index {cell.drainage_index:.2f} is below the development threshold {t['low_drainage']:.2f}.",
        ))
    if cell.soil_fertility_index < t["low_fertility"]:
        status = cell.nutrient_deficiency_status
        triggers.append(_trigger(
            "low_soil_fertility", "farm_context", 1.0 - cell.soil_fertility_index,
            f"Soil-fertility index {cell.soil_fertility_index:.2f} is below the development threshold {t['low_fertility']:.2f}.",
            status=status, confirmed=status in {EvidenceStatus.FIELD_CONFIRMED, EvidenceStatus.EXPERT_CONFIRMED},
        ))
    decline = max(cell.production_decline_fraction, production_decline_probability)
    if decline >= t["production_decline"]:
        triggers.append(_trigger(
            "production_decline", "production", decline,
            f"Production decline pressure is estimated at {decline:.1%}.",
            status=EvidenceStatus.PREDICTED, confirmed=False,
        ))
    if pest_probability >= t["pest_probability"]:
        triggers.append(_trigger(
            "pest_outbreak_risk", "pest", pest_probability,
            f"Maximum linked pest outbreak probability is {pest_probability:.1%}.",
            status=EvidenceStatus.FIELD_CONFIRMED if pest_confirmed else EvidenceStatus.PREDICTED,
            confirmed=pest_confirmed,
            evidence_ids=pest_evidence_ids,
        ))
    if cell.storm_damage_status is not None:
        confirmed = cell.storm_damage_status in {EvidenceStatus.FIELD_CONFIRMED, EvidenceStatus.EXPERT_CONFIRMED}
        triggers.append(_trigger(
            "storm_damage", "weather", 0.75 if confirmed else 0.45,
            "Storm damage was supplied in the cell context.",
            status=cell.storm_damage_status, confirmed=confirmed,
        ))
    if best_intercrop_score is not None and best_intercrop_score >= t["intercrop_suitability"]:
        triggers.append(_trigger(
            "intercropping_opportunity", "intercropping", best_intercrop_score / 100.0,
            f"Best linked intercrop suitability score is {best_intercrop_score:.1f}/100.",
        ))
    return triggers


def _priority(severity: float, confirmed: bool) -> str:
    score = severity + (0.15 if confirmed else 0)
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.40:
        return "moderate"
    if score >= 0.20:
        return "low"
    return "routine"


def _action(
    *, cell: RehabilitationCellContext, action_type: RehabilitationActionType,
    triggers: list[RehabilitationTrigger], planned_at, problem: str, cause: str,
    instructions: list[str], materials: list[str], timing: RehabilitationTiming,
    requires_confirmation: bool, production_regained: float,
) -> RehabilitationAction:
    severity = max((item.severity for item in triggers), default=0.1)
    confirmed = any(item.confirmed_damage for item in triggers)
    scheduled = planned_at.date() + timedelta(days=(
        PARAMETERS["inspection_delay_days"] if action_type == RehabilitationActionType.INSPECT
        else PARAMETERS["action_delay_days"]
    ))
    followups = [scheduled + timedelta(days=int(days)) for days in PARAMETERS["follow_up_days"]]
    cost = cost_estimate(action_type, cell.area_hectares)
    recovery_days = int(PARAMETERS["cost_catalog"][action_type.value]["recovery_days"])
    median = max(0.0, production_regained)
    return RehabilitationAction(
        cell_id=cell.cell_id,
        action_type=action_type,
        timing=timing,
        priority=_priority(severity, confirmed),
        problem_detected=problem,
        likely_cause=cause,
        triggers=triggers,
        evidence_ids=sorted({evidence for trigger in triggers for evidence in trigger.evidence_ids}, key=str),
        instructions=instructions,
        required_materials=materials,
        scheduled_date=scheduled,
        follow_up_dates=followups,
        cost=cost,
        expected_recovery_days=recovery_days,
        expected_production_regained_lower=median * 0.6,
        expected_production_regained_median=median,
        expected_production_regained_upper=median * 1.4,
        production_regained_unit=UnitCode.TONNE,
        confidence=ConfidenceLevel.MODERATE if confirmed else ConfidenceLevel.LOW,
        requires_field_confirmation=requires_confirmation,
        parameter_basis=(
            "Recovery and cost values are Phase 8 scenario assumptions for comparison, not a causal field guarantee."
        ),
    )


def generate_actions(
    cell: RehabilitationCellContext,
    triggers: list[RehabilitationTrigger],
    *, planned_at,
    cell_baseline_production_tonnes: float,
    pest_probability: float,
    pest_confirmed: bool,
    best_intercrop: dict[str, Any] | None,
) -> list[RehabilitationAction]:
    codes = {item.trigger_code for item in triggers}
    actions: list[RehabilitationAction] = []
    if triggers:
        actions.append(_action(
            cell=cell, action_type=RehabilitationActionType.INSPECT, triggers=triggers,
            planned_at=planned_at, problem="Cell requires field verification before irreversible action.",
            cause="One or more production, palm-state, weather, pest, soil, or opportunity triggers were detected.",
            instructions=[
                "Inspect palms and ground conditions using a georeferenced cell checklist.",
                "Record photographs, affected-palm counts, drainage, and symptom observations.",
                "Mark each finding as observed, farmer-reported, field-confirmed, or expert-confirmed.",
            ],
            materials=["inspection form", "camera or mobile device", "cell map"],
            timing=RehabilitationTiming.POST_EVENT_INSPECTION,
            requires_confirmation=False, production_regained=0.0,
        ))
    if "poor_drainage" in codes:
        related = [item for item in triggers if item.trigger_code == "poor_drainage"]
        actions.append(_action(
            cell=cell, action_type=RehabilitationActionType.DRAINAGE_IMPROVEMENT,
            triggers=related, planned_at=planned_at,
            problem="Persistent drainage limitation can increase waterlogging and disease pressure.",
            cause="Low cell drainage index.",
            instructions=["Confirm outlet direction and safe discharge point.", "Clear existing drains before excavating new channels.", "Reassess water persistence after rainfall."],
            materials=["drainage tools", "protective equipment", "erosion-control materials"],
            timing=RehabilitationTiming.ROUTINE, requires_confirmation=True,
            production_regained=cell_baseline_production_tonnes * 0.05,
        ))
    if "low_soil_fertility" in codes or "environmental_stress" in codes:
        related = [item for item in triggers if item.trigger_code in {"low_soil_fertility", "environmental_stress"}]
        actions.append(_action(
            cell=cell, action_type=RehabilitationActionType.ORGANIC_MATTER_APPLICATION,
            triggers=related, planned_at=planned_at,
            problem="Low fertility or stress may limit recovery.", cause="Low soil-fertility index or elevated stressed-palm share.",
            instructions=["Obtain or confirm a soil assessment.", "Apply only locally appropriate organic material.", "Record material type, amount, date, and treated area."],
            materials=["locally appropriate organic material", "application tools", "record sheet"],
            timing=RehabilitationTiming.ROUTINE, requires_confirmation=True,
            production_regained=cell_baseline_production_tonnes * 0.04,
        ))
        nutrient_statuses = {item.evidence_status for item in related}
        confirmed_nutrient = bool(nutrient_statuses & {EvidenceStatus.FIELD_CONFIRMED, EvidenceStatus.EXPERT_CONFIRMED})
        if confirmed_nutrient:
            actions.append(_action(
                cell=cell, action_type=RehabilitationActionType.FERTILIZER_CORRECTION,
                triggers=related, planned_at=planned_at,
                problem="Confirmed nutrient limitation requires a correction plan.", cause="Field- or expert-confirmed nutrient evidence.",
                instructions=["Use a soil-test- and expert-based nutrient plan.", "Do not infer chemical dosage from COCOAID.", "Record application and follow-up observations."],
                materials=["expert-approved nutrient inputs", "protective equipment", "application record"],
                timing=RehabilitationTiming.POST_CONFIRMATION, requires_confirmation=False,
                production_regained=cell_baseline_production_tonnes * 0.07,
            ))
    if "pest_outbreak_risk" in codes or "recorded_infested_share" in codes:
        related = [item for item in triggers if item.trigger_code in {"pest_outbreak_risk", "recorded_infested_share"}]
        actions.append(_action(
            cell=cell, action_type=RehabilitationActionType.SANITATION,
            triggers=related, planned_at=planned_at,
            problem="Pest or disease pressure may be supported by poor sanitation or infested material.",
            cause=f"Pest pressure {pest_probability:.1%} and/or recorded infested palms.",
            instructions=["Remove or isolate confirmed breeding and infested material according to PCA guidance.", "Keep a count and location record.", "Escalate quarantine-sensitive findings to the responsible authority."],
            materials=["sanitation tools", "protective equipment", "marked disposal or isolation area"],
            timing=RehabilitationTiming.POST_CONFIRMATION if pest_confirmed else RehabilitationTiming.POST_EVENT_INSPECTION,
            requires_confirmation=not pest_confirmed,
            production_regained=cell_baseline_production_tonnes * 0.04,
        ))
        if pest_confirmed:
            actions.append(_action(
                cell=cell, action_type=RehabilitationActionType.PEST_OR_DISEASE_TREATMENT,
                triggers=related, planned_at=planned_at,
                problem="Confirmed pest or disease evidence requires a pest-specific management plan.",
                cause="Linked field-confirmed pest evidence.",
                instructions=["Follow the linked PCA integrated-management actions.", "Obtain expert confirmation before any chemical intervention.", "Do not use COCOAID as a pesticide dosage source."],
                materials=["PCA-recommended non-chemical management materials", "protective equipment", "monitoring forms"],
                timing=RehabilitationTiming.POST_CONFIRMATION, requires_confirmation=False,
                production_regained=cell_baseline_production_tonnes * 0.07,
            ))
    dead_fraction = cell.dead_palms / cell.total_palms
    if "dead_or_nonproductive_palms" in codes:
        action_type = (
            RehabilitationActionType.COMPLETE_REPLANTING
            if dead_fraction >= PARAMETERS["trigger_thresholds"]["dead_fraction_complete"]
            else RehabilitationActionType.PARTIAL_REPLANTING
        )
        related = [item for item in triggers if item.trigger_code in {"dead_or_nonproductive_palms", "excessive_aging_share"}]
        actions.append(_action(
            cell=cell, action_type=action_type, triggers=related, planned_at=planned_at,
            problem="Dead planting positions reduce productive stand density.", cause="Recorded dead palms and possibly excessive aging.",
            instructions=["Verify mortality and map replacement positions.", "Confirm suitable variety and planting material source.", "Plan establishment care and survival checks."],
            materials=["verified planting material", "planting tools", "establishment supplies"],
            timing=RehabilitationTiming.POST_CONFIRMATION, requires_confirmation=True,
            production_regained=cell_baseline_production_tonnes * min(0.12, dead_fraction * 0.5),
        ))
    if best_intercrop and best_intercrop.get("suitability_score", 0) >= PARAMETERS["trigger_thresholds"]["intercrop_suitability"]:
        related = [item for item in triggers if item.trigger_code == "intercropping_opportunity"]
        actions.append(_action(
            cell=cell, action_type=RehabilitationActionType.INTERCROPPING_ADJUSTMENT,
            triggers=related, planned_at=planned_at,
            problem="Suitable understory space may be underutilized.",
            cause=f"Linked assessment identifies {best_intercrop.get('candidate_id')} at {best_intercrop.get('suitability_score'):.1f}/100.",
            instructions=["Verify the recommended cell and planting layout in the field.", "Confirm water, labor, pest compatibility, and market access.", "Protect coconut root zones and drainage paths."],
            materials=["candidate planting material", "layout stakes", "establishment inputs"],
            timing=RehabilitationTiming.ROUTINE, requires_confirmation=True,
            production_regained=cell_baseline_production_tonnes * 0.01,
        ))
    return actions


SCENARIO_ACTIONS: dict[ScenarioType, set[RehabilitationActionType]] = {
    "no_action": set(),
    "pest_management": {
        RehabilitationActionType.INSPECT, RehabilitationActionType.MONITOR,
        RehabilitationActionType.SANITATION, RehabilitationActionType.REMOVE_BREEDING_MATERIAL,
        RehabilitationActionType.PEST_OR_DISEASE_TREATMENT,
        RehabilitationActionType.PRUNING_OR_CROWN_MANAGEMENT,
    },
    "fertilization": {
        RehabilitationActionType.INSPECT, RehabilitationActionType.ORGANIC_MATTER_APPLICATION,
        RehabilitationActionType.FERTILIZER_CORRECTION, RehabilitationActionType.DRAINAGE_IMPROVEMENT,
    },
    "replanting": {
        RehabilitationActionType.INSPECT, RehabilitationActionType.PARTIAL_REPLANTING,
        RehabilitationActionType.COMPLETE_REPLANTING, RehabilitationActionType.VARIETY_REPLACEMENT,
    },
    "intercropping": {RehabilitationActionType.INSPECT, RehabilitationActionType.INTERCROPPING_ADJUSTMENT},
    "combined_rehabilitation": set(RehabilitationActionType),
}


def evaluate_scenario(
    scenario_type: ScenarioType,
    *, actions: list[RehabilitationAction], baseline_lower: float, baseline_median: float,
    baseline_upper: float, baseline_severe_loss_probability: float,
    intercrop_revenue: tuple[float, float, float], budget: float | None,
    available_labor: float | None, annual_discount_rate: float,
    planning_horizon_months: int, risk_aversion: float,
) -> RehabilitationScenarioResult:
    selected = [item for item in actions if item.action_type in SCENARIO_ACTIONS[scenario_type]]
    cost = sum(item.cost.total_php for item in selected)
    labor = sum(item.cost.labor_person_days or 0.0 for item in selected)
    status = "feasible"
    reasons: list[str] = []
    if scenario_type != "no_action" and not selected:
        status = "not_applicable"
        reasons.append("No generated actions belong to this scenario.")
    if budget is not None and cost > budget + 0.01:
        status = "infeasible_budget"
        reasons.append(f"Scenario cost PHP {cost:,.2f} exceeds budget PHP {budget:,.2f}.")
    if available_labor is not None and labor > available_labor + 1e-9:
        status = "infeasible_labor"
        reasons.append(f"Scenario labor {labor:.2f} person-days exceeds available {available_labor:.2f}.")

    effect = PARAMETERS["scenario_effects"][scenario_type]
    horizon_factor = min(1.0, planning_horizon_months / 24.0)
    recovery = effect["recovery"] * horizon_factor
    residual_risk = clamp(baseline_severe_loss_probability * (1.0 - effect["risk_reduction"]))
    loss_fraction = PARAMETERS["risk_penalty_loss_fraction"]
    production_multiplier = max(0.0, 1.0 - residual_risk * loss_fraction + recovery)
    lower = baseline_lower * production_multiplier
    median = baseline_median * production_multiplier
    upper = baseline_upper * production_multiplier

    revenue = intercrop_revenue if scenario_type in {"intercropping", "combined_rehabilitation"} else (0.0, 0.0, 0.0)
    years = planning_horizon_months / 12.0
    discount = (1.0 + annual_discount_rate) ** max(years, 0.0)
    production_value = median * PARAMETERS["coconut_value_php_per_tonne"]
    benefit = production_value + revenue[1] / discount
    risk_penalty = risk_aversion * residual_risk * baseline_median * loss_fraction * PARAMETERS["coconut_value_php_per_tonne"]
    utility = benefit - cost - risk_penalty
    if status != "feasible":
        utility = -1e18
    return RehabilitationScenarioResult(
        scenario_type=scenario_type,
        status=status,
        action_ids=[item.action_id for item in selected],
        total_cost_php=round(cost, 2),
        labor_person_days=round(labor, 2),
        coconut_production_lower_tonnes=round(lower, 6),
        coconut_production_median_tonnes=round(median, 6),
        coconut_production_upper_tonnes=round(upper, 6),
        intercrop_gross_revenue_lower_php=round(revenue[0], 2),
        intercrop_gross_revenue_median_php=round(revenue[1], 2),
        intercrop_gross_revenue_upper_php=round(revenue[2], 2),
        severe_loss_probability=residual_risk,
        expected_utility=utility,
        utility_components={
            "discounted_benefit_php": benefit,
            "cost_php": cost,
            "risk_penalty_php": risk_penalty,
            "development_coconut_value_php_per_tonne": PARAMETERS["coconut_value_php_per_tonne"],
        },
        feasibility_reasons=reasons,
        assumptions=[
            "Scenario effects and costs are development parameters pending field and local-price validation.",
            "Intercrop values are gross-revenue scenarios only where a linked aggregate profile exists.",
            "Utility is comparative and must not be interpreted as guaranteed profit.",
        ],
    )
