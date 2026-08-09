from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from app.bayesian import repository as bayesian_repository
from app.core.errors import EngineExecutionError
from app.domain.enums import EngineAvailability, EngineMaturity
from app.domain.provenance import RunProvenance, VersionReference
from app.domain.rehabilitation import (
    RehabilitationEngineOutput,
    RehabilitationEngineSummary,
    RehabilitationPlan,
    RehabilitationPlanRequest,
)
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.engines.registry import engine_registry
from app.production import repository as production_repository
from app.rehabilitation import repository
from app.rehabilitation.parameters import (
    REHABILITATION_COST_CATALOG_VERSION,
    REHABILITATION_ENGINE_VERSION,
    REHABILITATION_PARAMETER_VERSION,
)
from app.rehabilitation.planner import detect_cell_triggers, evaluate_scenario, generate_actions

REHABILITATION_DATA_NOTICE = (
    "Phase 8 provides transparent rehabilitation and scenario-comparison logic. Costs, labor, recovery, "
    "coconut value, and utility coefficients are versioned development assumptions pending local and field validation. "
    "Predicted hazards and inferred pest risks trigger inspection and preparation, not automatic confirmation of damage, "
    "pest diagnosis, chemical dosage, or irreversible treatment."
)

REHABILITATION_DESCRIPTOR = EngineDescriptor(
    engine_id="v3.rehabilitation",
    name="Rehabilitation and Scenario Optimization Engine",
    version=REHABILITATION_ENGINE_VERSION,
    maturity=EngineMaturity.EXPERIMENTAL,
    availability=EngineAvailability.AVAILABLE,
    input_contract="RehabilitationPlanRequest",
    output_contract="RehabilitationEngineOutput",
    dependencies=["v3.production", "v3.bayesian", "v3.pest_inference", "v3.intercropping"],
    limitations=[
        "Cost and labor catalog requires local validation.",
        "Recovery effects are scenario assumptions rather than causal field estimates.",
        "No pesticide dosage is generated.",
        "Predicted events are not treated as confirmed damage.",
    ],
)


class RehabilitationEngine(AnalyticalEngine[RehabilitationPlanRequest, RehabilitationEngineOutput]):
    descriptor = REHABILITATION_DESCRIPTOR
    input_model = RehabilitationPlanRequest
    output_model = RehabilitationEngineOutput

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path

    def _run(self, payload: RehabilitationPlanRequest, context: EngineExecutionContext):
        forecast = production_repository.get_forecast(
            payload.production_forecast_id, database_path=self.database_path
        )
        if not forecast:
            raise EngineExecutionError("Production forecast not found")
        if forecast["farm_id"] != str(payload.farm_id):
            raise EngineExecutionError("farm_id does not match production forecast")
        snapshot = production_repository.get_feature_snapshot(
            forecast["feature_snapshot_id"], database_path=self.database_path
        )
        if not snapshot:
            raise EngineExecutionError("Production feature snapshot not found")
        weather_run_id = UUID(snapshot["weather_run_id"])

        warnings: list[str] = []
        adjusted = float(forecast["variety_adjusted_prediction"])
        baseline_lower, baseline_median, baseline_upper = adjusted * 0.85, adjusted, adjusted * 1.15
        decline_probability = float(forecast.get("probability_of_decline") or 0.20)
        posterior = None
        if payload.posterior_id:
            posterior = bayesian_repository.get_posterior(
                payload.posterior_id, database_path=self.database_path
            )
            if not posterior:
                raise EngineExecutionError("Bayesian posterior not found")
            if posterior["farm_id"] != str(payload.farm_id):
                raise EngineExecutionError("posterior farm_id does not match request")
            if posterior["production_forecast_id"] != str(payload.production_forecast_id):
                raise EngineExecutionError("posterior does not belong to production forecast")
            distribution = posterior["production_distribution"]
            baseline_lower = float(distribution["lower"])
            baseline_median = float(distribution["median"])
            baseline_upper = float(distribution["upper"])
            decline_probability = float(posterior["probability_of_decline"])
        else:
            warnings.append("No Bayesian posterior supplied; Phase 4 prediction with bounded development uncertainty was used.")

        pest_probability = 0.0
        pest_confirmed = False
        pest_evidence_ids: list[UUID] = []
        if payload.pest_assessment_run_id:
            pest_run = repository.load_pest_run(
                payload.pest_assessment_run_id, database_path=self.database_path
            )
            if not pest_run:
                raise EngineExecutionError("Pest assessment run not found")
            if pest_run["farm_id"] != str(payload.farm_id):
                raise EngineExecutionError("pest assessment farm_id does not match request")
            if pest_run["production_forecast_id"] != str(payload.production_forecast_id):
                raise EngineExecutionError("pest assessment does not belong to production forecast")
            pest_probability = max(
                (float(item["outbreak_probability"]) for item in pest_run["assessments"]),
                default=0.0,
            )
            for item in pest_run["observations"]:
                if item["evidence_status"] in {"field_confirmed", "expert_confirmed"}:
                    pest_confirmed = True
                    pest_evidence_ids.append(UUID(item["id"]))
        else:
            warnings.append("No Phase 6 pest assessment supplied; pest-conditioned actions are limited to cell inventory evidence.")

        intercrop_by_cell: dict[str, dict] = {}
        intercrop_revenue = [0.0, 0.0, 0.0]
        if payload.intercropping_run_id:
            intercrop_run = repository.load_intercropping_run(
                payload.intercropping_run_id, database_path=self.database_path
            )
            if not intercrop_run:
                raise EngineExecutionError("Intercropping assessment run not found")
            if intercrop_run["farm_id"] != str(payload.farm_id):
                raise EngineExecutionError("intercropping assessment farm_id does not match request")
            if intercrop_run["production_forecast_id"] != str(payload.production_forecast_id):
                raise EngineExecutionError("intercropping assessment does not belong to production forecast")
            for item in intercrop_run["assessments"]:
                current = intercrop_by_cell.get(item["cell_id"])
                if current is None or item["suitability_score"] > current["suitability_score"]:
                    intercrop_by_cell[item["cell_id"]] = item
            for item in intercrop_by_cell.values():
                economics = item["economic_potential"]
                if economics.get("status") == "available":
                    intercrop_revenue[0] += float(economics.get("gross_revenue_lower_php") or 0)
                    intercrop_revenue[1] += float(economics.get("gross_revenue_median_php") or 0)
                    intercrop_revenue[2] += float(economics.get("gross_revenue_upper_php") or 0)
        else:
            warnings.append("No Phase 7 intercropping run supplied; intercropping opportunity and revenue are unavailable.")

        total_area = sum(cell.area_hectares for cell in payload.cells)
        all_actions = []
        all_triggers = []
        critical_cells = []
        for cell in payload.cells:
            share = cell.area_hectares / total_area
            baseline_cell = baseline_median * share
            best = intercrop_by_cell.get(str(cell.cell_id))
            triggers = detect_cell_triggers(
                cell,
                pest_probability=pest_probability,
                pest_confirmed=pest_confirmed,
                pest_evidence_ids=pest_evidence_ids,
                production_decline_probability=decline_probability,
                best_intercrop_score=float(best["suitability_score"]) if best else None,
            )
            all_triggers.extend(triggers)
            if max((trigger.severity for trigger in triggers), default=0.0) >= 0.65:
                critical_cells.append(cell.cell_id)
            all_actions.extend(generate_actions(
                cell,
                triggers,
                planned_at=payload.planned_at,
                cell_baseline_production_tonnes=baseline_cell,
                pest_probability=pest_probability,
                pest_confirmed=pest_confirmed,
                best_intercrop=best,
            ))

        severe_loss_probability = max(decline_probability, pest_probability)
        if posterior:
            severe_loss_probability = max(
                severe_loss_probability,
                float(posterior["probability_of_tree_mortality"]),
                float(posterior["probability_of_pest_outbreak"]),
            )
        scenario_types = [
            "no_action", "pest_management", "fertilization", "replanting",
            "intercropping", "combined_rehabilitation",
        ]
        scenarios = [
            evaluate_scenario(
                scenario,
                actions=all_actions,
                baseline_lower=baseline_lower,
                baseline_median=baseline_median,
                baseline_upper=baseline_upper,
                baseline_severe_loss_probability=severe_loss_probability,
                intercrop_revenue=tuple(intercrop_revenue),
                budget=payload.total_budget_php,
                available_labor=payload.available_labor_person_days,
                annual_discount_rate=payload.annual_discount_rate,
                planning_horizon_months=payload.planning_horizon_months,
                risk_aversion=payload.risk_aversion,
            )
            for scenario in scenario_types
        ]
        feasible = [item for item in scenarios if item.status == "feasible"]
        selected = max(feasible, key=lambda item: item.expected_utility)
        selected_ids = set(selected.action_ids)
        selected_actions = [item for item in all_actions if item.action_id in selected_ids]
        field_confirmation_required = any(item.requires_field_confirmation for item in selected_actions)
        unallocated = None
        if payload.total_budget_php is not None:
            unallocated = max(0.0, payload.total_budget_php - selected.total_cost_php)

        provenance = RunProvenance(
            farm_data_version=payload.farm_data_version,
            weather_run_id=weather_run_id,
            model_versions=[
                VersionReference(component="production", version=forecast["model_version"]),
                VersionReference(component="rehabilitation", version=REHABILITATION_ENGINE_VERSION),
            ],
            parameter_versions=[
                VersionReference(component="rehabilitation", version=REHABILITATION_PARAMETER_VERSION),
                VersionReference(component="rehabilitation_costs", version=REHABILITATION_COST_CATALOG_VERSION),
            ],
            warnings=warnings,
            limitations=[
                "Scenario utility is comparative and not guaranteed profit.",
                "Cost, labor, and recovery values require local validation.",
            ],
        )
        plan = RehabilitationPlan(
            rehabilitation_plan_id=uuid4(),
            farm_id=payload.farm_id,
            production_forecast_id=payload.production_forecast_id,
            posterior_id=payload.posterior_id,
            pest_assessment_run_id=payload.pest_assessment_run_id,
            intercropping_run_id=payload.intercropping_run_id,
            actions=all_actions,
            scenarios=scenarios,
            selected_scenario=selected.scenario_type,
            total_budget_php=payload.total_budget_php,
            total_expected_cost_php=selected.total_cost_php,
            expected_recovery_summary=(
                f"Selected {selected.scenario_type} with {len(selected_actions)} action(s), "
                f"median coconut production scenario {selected.coconut_production_median_tonnes:.3f} t, "
                f"and severe-loss probability {selected.severe_loss_probability:.1%}."
            ),
            no_action_comparison_id=next(item.scenario_id for item in scenarios if item.scenario_type == "no_action"),
            unallocated_budget_php=unallocated,
            warnings=warnings,
            data_notice=REHABILITATION_DATA_NOTICE,
            provenance=provenance,
        )
        summary = RehabilitationEngineSummary(
            assessed_cell_count=len(payload.cells),
            trigger_count=len(all_triggers),
            candidate_action_count=len(all_actions),
            feasible_scenario_count=len(feasible),
            selected_scenario=selected.scenario_type,
            selected_cost_php=selected.total_cost_php,
            selected_labor_person_days=selected.labor_person_days,
            critical_cell_ids=critical_cells,
            field_confirmation_required=field_confirmation_required,
        )
        output = RehabilitationEngineOutput(
            plan=plan,
            summary=summary,
            parameter_version=REHABILITATION_PARAMETER_VERSION,
            cost_catalog_version=REHABILITATION_COST_CATALOG_VERSION,
            linked_weather_run_id=weather_run_id,
            warnings=warnings,
        )
        repository.save_output(
            output, request_payload=payload.model_dump(mode="json"), database_path=self.database_path
        )
        return output, warnings


rehabilitation_engine = RehabilitationEngine()
engine_registry.register(rehabilitation_engine)
