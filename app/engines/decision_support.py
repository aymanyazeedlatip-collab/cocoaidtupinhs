from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from app.bayesian import repository as bayesian_repository
from app.core.errors import EngineExecutionError
from app.decision_support import repository
from app.decision_support.parameters import (
    DECISION_SUPPORT_ENGINE_VERSION,
    DECISION_SUPPORT_PARAMETER_VERSION,
    DEPENDENCY_GRAPH,
    DEPENDENCY_GRAPH_VERSION,
    PRIORITY_ORDER,
)
from app.domain.decision_support import (
    DecisionComponentResult,
    DecisionEvidence,
    DecisionOverview,
    DecisionRecommendation,
    DecisionSupportEngineOutput,
    DecisionSupportRecord,
    DecisionSupportRequest,
    DecisionSupportSummary,
    DecisionTraceEdge,
)
from app.domain.enums import ConfidenceLevel, EngineAvailability, EngineMaturity
from app.domain.provenance import RunProvenance, VersionReference
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.intercropping import repository as intercropping_repository
from app.pest import repository as pest_repository
from app.production import repository as production_repository
from app.rehabilitation import repository as rehabilitation_repository

DECISION_SUPPORT_DATA_NOTICE = (
    "This record consolidates outputs produced by the versioned COCOAID analytical engines. "
    "Recommendations are deterministic interpretations of stored model outputs and reference rules; "
    "they are not an official PCA diagnosis, guaranteed income, or substitute for field verification."
)

DECISION_SUPPORT_DESCRIPTOR = EngineDescriptor(
    engine_id="v3.decision_support",
    name="Integrated Decision-Support Network",
    version=DECISION_SUPPORT_ENGINE_VERSION,
    maturity=EngineMaturity.EXPERIMENTAL,
    availability=EngineAvailability.AVAILABLE,
    input_contract="DecisionSupportRequest",
    output_contract="DecisionSupportEngineOutput",
    dependencies=[
        "v3.production", "v3.bayesian", "v3.pest_inference",
        "v3.intercropping", "v3.rehabilitation",
    ],
    limitations=[
        "Consolidates previously computed engine outputs rather than replacing their scientific logic.",
        "Recommendations require field verification where source evidence is predicted, suspected, or incomplete.",
    ],
)

ENGINE_IDS = {
    "production": "v3.production",
    "bayesian": "v3.bayesian",
    "pest": "v3.pest_inference",
    "intercropping": "v3.intercropping",
    "rehabilitation": "v3.rehabilitation",
}


class DecisionSupportEngine(AnalyticalEngine[DecisionSupportRequest, DecisionSupportEngineOutput]):
    descriptor = DECISION_SUPPORT_DESCRIPTOR
    input_model = DecisionSupportRequest
    output_model = DecisionSupportEngineOutput

    def __init__(self, *, database_path: Path | None = None) -> None:
        self.database_path = database_path

    def _run(
        self,
        payload: DecisionSupportRequest,
        context: EngineExecutionContext,
    ) -> tuple[DecisionSupportEngineOutput, list[str]]:
        components: list[DecisionComponentResult] = []
        warnings: list[str] = []
        records: dict[str, dict[str, Any] | None] = {}

        production = production_repository.get_forecast(
            payload.production_forecast_id, database_path=self.database_path
        )
        if not production:
            raise EngineExecutionError("Production forecast not found")
        if production["farm_id"] != str(payload.farm_id):
            raise EngineExecutionError("Production forecast farm_id does not match request")
        records["production"] = production
        components.append(DecisionComponentResult(
            component="production",
            engine_id=ENGINE_IDS["production"],
            status="succeeded",
            record_id=payload.production_forecast_id,
            summary={
                "raw_ml_prediction": production["raw_ml_prediction"],
                "variety_adjusted_prediction": production["variety_adjusted_prediction"],
                "unit": production["unit"],
                "model_version": production["model_version"],
                "posterior_status": production["posterior_status"],
            },
        ))

        optional_ids = {
            "bayesian": payload.posterior_id,
            "pest": payload.pest_assessment_run_id,
            "intercropping": payload.intercropping_run_id,
            "rehabilitation": payload.rehabilitation_plan_id,
        }
        loaders = {
            "bayesian": lambda value: bayesian_repository.get_posterior(value, database_path=self.database_path),
            "pest": lambda value: rehabilitation_repository.load_pest_run(value, database_path=self.database_path),
            "intercropping": lambda value: rehabilitation_repository.load_intercropping_run(value, database_path=self.database_path),
            "rehabilitation": lambda value: rehabilitation_repository.get_plan(value, database_path=self.database_path),
        }

        for component in ("bayesian", "pest", "intercropping", "rehabilitation"):
            if component not in payload.requested_components:
                records[component] = None
                components.append(DecisionComponentResult(
                    component=component,
                    engine_id=ENGINE_IDS[component],
                    status="skipped",
                    warnings=["Component was not requested."],
                ))
                continue
            record_id = optional_ids[component]
            if record_id is None:
                records[component] = None
                message = f"No {component} record ID was supplied."
                warnings.append(message)
                components.append(DecisionComponentResult(
                    component=component,
                    engine_id=ENGINE_IDS[component],
                    status="skipped",
                    warnings=[message],
                ))
                continue
            try:
                record = loaders[component](record_id)
                if not record:
                    raise ValueError(f"{component} record not found")
                self._validate_record_links(component, record, payload)
                records[component] = record
                components.append(DecisionComponentResult(
                    component=component,
                    engine_id=ENGINE_IDS[component],
                    status="succeeded",
                    record_id=record_id,
                    summary=self._component_summary(component, record),
                ))
            except Exception as exc:
                records[component] = None
                message = str(exc) or f"Unable to resolve {component} record"
                components.append(DecisionComponentResult(
                    component=component,
                    engine_id=ENGINE_IDS[component],
                    status="failed",
                    record_id=record_id,
                    errors=[message],
                ))
                warnings.append(f"{component}: {message}")
                if payload.failure_policy == "strict":
                    raise EngineExecutionError(
                        f"Strict decision-support run failed while resolving {component}",
                        details={"component": component, "error": message},
                    ) from exc

        recommendations = self._recommendations(payload, records)
        recommendations.sort(
            key=lambda item: (
                -PRIORITY_ORDER[item.priority],
                item.category,
                item.title,
            )
        )
        traceability = self._traceability(components)
        overview = self._overview(records, recommendations, payload.requested_components, components)
        failed = sum(item.status == "failed" for item in components)
        skipped = sum(item.status == "skipped" for item in components if item.component in payload.requested_components)
        succeeded = sum(item.status == "succeeded" for item in components)
        status = "completed" if failed == 0 and skipped == 0 else "partially_completed"

        provenance = RunProvenance(
            farm_data_version=payload.farm_data_version,
            weather_run_id=self._weather_run_id(production),
            model_versions=[
                VersionReference(component="decision_support", version=DECISION_SUPPORT_ENGINE_VERSION),
                VersionReference(component="production", version=production["model_version"]),
            ],
            parameter_versions=[
                VersionReference(component="decision_support", version=DECISION_SUPPORT_PARAMETER_VERSION),
                VersionReference(component="dependency_graph", version=DEPENDENCY_GRAPH_VERSION),
            ],
            warnings=warnings,
            limitations=[
                "The network summarizes saved engine outputs and does not create new agronomic evidence.",
                "Local cost, yield, pest, and intercropping assumptions require field and expert validation.",
            ],
        )
        record = DecisionSupportRecord(
            farm_id=payload.farm_id,
            generated_at=payload.generated_at,
            status=status,
            requested_components=payload.requested_components,
            component_results=components,
            overview=overview,
            recommendations=recommendations,
            traceability=traceability,
            provenance=provenance,
            warnings=warnings,
            data_notice=DECISION_SUPPORT_DATA_NOTICE,
        )
        summary = DecisionSupportSummary(
            analysis_run_id=record.analysis_run_id,
            status=status,
            succeeded_components=succeeded,
            skipped_components=skipped,
            failed_components=failed,
            recommendation_count=len(recommendations),
            urgent_recommendation_count=overview.urgent_recommendation_count,
            data_completeness=overview.data_completeness,
        )
        output = DecisionSupportEngineOutput(
            record=record,
            summary=summary,
            parameter_version=DECISION_SUPPORT_PARAMETER_VERSION,
            dependency_graph_version=DEPENDENCY_GRAPH_VERSION,
            warnings=warnings,
        )
        repository.save_output(output, database_path=self.database_path)
        return output, warnings

    @staticmethod
    def _validate_record_links(component: str, record: dict[str, Any], payload: DecisionSupportRequest) -> None:
        if record.get("farm_id") != str(payload.farm_id):
            raise ValueError(f"{component} farm_id does not match request")
        if component == "bayesian":
            linked = record.get("production_forecast_id")
        elif component == "pest":
            linked = record.get("production_forecast_id")
        elif component == "intercropping":
            linked = record.get("production_forecast_id")
        else:
            linked = record.get("production_forecast_id")
        if linked and linked != str(payload.production_forecast_id):
            raise ValueError(f"{component} record does not belong to production forecast")

    @staticmethod
    def _component_summary(component: str, record: dict[str, Any]) -> dict[str, Any]:
        if component == "bayesian":
            return {
                "production_distribution": record.get("production_distribution"),
                "probability_of_decline": record.get("probability_of_decline"),
                "probability_of_recovery": record.get("probability_of_recovery"),
                "probability_of_tree_mortality": record.get("probability_of_tree_mortality"),
                "probability_of_pest_outbreak": record.get("probability_of_pest_outbreak"),
            }
        if component == "pest":
            assessments = record.get("assessments", [])
            highest = max(assessments, key=lambda item: item["outbreak_probability"], default=None)
            return {"assessment_count": len(assessments), "highest_risk": highest}
        if component == "intercropping":
            assessments = record.get("assessments", [])
            best = max(assessments, key=lambda item: item["suitability_score"], default=None)
            return {"assessment_count": len(assessments), "best_candidate": best}
        scenarios = record.get("scenarios", [])
        selected = next((item for item in scenarios if item["scenario_type"] == record.get("selected_scenario")), None)
        return {
            "selected_scenario": record.get("selected_scenario"),
            "selected_scenario_result": selected,
            "action_count": len(record.get("actions", [])),
        }

    def _recommendations(
        self,
        payload: DecisionSupportRequest,
        records: dict[str, dict[str, Any] | None],
    ) -> list[DecisionRecommendation]:
        result: list[DecisionRecommendation] = []
        production = records["production"] or {}
        estimate = float(production.get("variety_adjusted_prediction") or production.get("raw_ml_prediction") or 0)
        result.append(DecisionRecommendation(
            category="production",
            priority="routine",
            title="Use the versioned production estimate as the planning baseline",
            action=f"Plan current operations around the recorded estimate of {estimate:.3f} {production.get('unit', '')}, while retaining the model and weather-run identifiers.",
            rationale="The production engine provides the common baseline used by downstream Bayesian, pest, intercropping, and rehabilitation analyses.",
            confidence=ConfidenceLevel.MODERATE,
            source_components=["production"],
            evidence=[DecisionEvidence(
                source_component="production", source_engine=ENGINE_IDS["production"],
                record_id=str(payload.production_forecast_id), field="variety_adjusted_prediction",
                value=estimate, explanation="Versioned production estimate used by all downstream modules.",
            )],
            limitations=["The retained production model remains a research baseline pending expanded field validation."],
        ))

        posterior = records.get("bayesian")
        if posterior:
            decline = float(posterior.get("probability_of_decline") or 0)
            mortality = float(posterior.get("probability_of_tree_mortality") or 0)
            if decline >= 0.5 or mortality >= 0.3:
                priority = "critical" if decline >= 0.75 or mortality >= 0.5 else "high"
                result.append(DecisionRecommendation(
                    category="uncertainty",
                    priority=priority,
                    title="Prioritize field verification of projected farm decline",
                    action="Inspect the highest-risk cells, verify palm condition and recent production, then record confirmed evidence before irreversible intervention.",
                    rationale=f"The Bayesian posterior estimates decline probability at {decline:.1%} and additional mortality probability at {mortality:.1%}.",
                    confidence=ConfidenceLevel.MODERATE,
                    source_components=["bayesian"],
                    evidence=[
                        DecisionEvidence(source_component="bayesian", source_engine=ENGINE_IDS["bayesian"], record_id=str(payload.posterior_id), field="probability_of_decline", value=decline, explanation="Posterior probability of production decline."),
                        DecisionEvidence(source_component="bayesian", source_engine=ENGINE_IDS["bayesian"], record_id=str(payload.posterior_id), field="probability_of_tree_mortality", value=mortality, explanation="Posterior probability of additional tree mortality."),
                    ],
                    requires_field_confirmation=True,
                    limitations=["Posterior probabilities are conditional on the entered farm state, evidence, and parameter assumptions."],
                ))

        pest_run = records.get("pest")
        if pest_run and pest_run.get("assessments"):
            top = max(pest_run["assessments"], key=lambda item: item["outbreak_probability"])
            probability = float(top["outbreak_probability"])
            priority = "critical" if probability >= 0.8 else "high" if probability >= 0.6 else "moderate" if probability >= 0.35 else "low"
            assessment = pest_repository.get_assessment(top["assessment_id"], database_path=self.database_path)
            actions = assessment.get("management_actions", []) if assessment else []
            action_text = actions[0]["action_text"] if actions else "Schedule a targeted field inspection and record symptom evidence."
            result.append(DecisionRecommendation(
                category="pest",
                priority=priority,
                title=f"Inspect for {top['pest_profile_id']}",
                action=action_text,
                rationale=f"This profile has the highest current outbreak probability at {probability:.1%}; expected and conditional losses remain separate in the source assessment.",
                confidence=ConfidenceLevel.MODERATE,
                source_components=["pest"],
                evidence=[DecisionEvidence(
                    source_component="pest", source_engine=ENGINE_IDS["pest"],
                    record_id=str(top["assessment_id"]), field="outbreak_probability",
                    value=probability, explanation="Highest pest-specific outbreak probability in the linked run.",
                )],
                requires_field_confirmation=True,
                limitations=["Risk inference is not a laboratory diagnosis and does not authorize unverified pesticide dosage."],
            ))

        intercrop_run = records.get("intercropping")
        if intercrop_run and intercrop_run.get("assessments"):
            eligible = [item for item in intercrop_run["assessments"] if item.get("hard_constraint_passed")]
            if eligible:
                best = max(eligible, key=lambda item: item["suitability_score"])
                full = intercropping_repository.get_assessment(best["assessment_id"], database_path=self.database_path)
                score = float(best["suitability_score"])
                priority = "moderate" if score >= 70 else "low"
                result.append(DecisionRecommendation(
                    category="intercropping",
                    priority=priority,
                    title=f"Evaluate a field trial for {best['candidate_id']}",
                    action=f"Use the recommended layout for cell {best['cell_label']}, beginning with a limited trial and monitoring coconut competition, water demand, and pest compatibility.",
                    rationale=f"The candidate achieved a decomposable suitability score of {score:.1f}/100 and passed the engine's hard constraints.",
                    confidence=ConfidenceLevel.MODERATE,
                    source_components=["intercropping"],
                    evidence=[DecisionEvidence(
                        source_component="intercropping", source_engine=ENGINE_IDS["intercropping"],
                        record_id=str(best["assessment_id"]), field="suitability_score",
                        value=score, explanation="Highest hard-constraint-passing intercrop score in the linked run.",
                    )],
                    limitations=(full.get("data_quality_notes", []) if full else [])[:10],
                ))

        plan = records.get("rehabilitation")
        if plan:
            selected = next(
                (item for item in plan.get("scenarios", []) if item["scenario_type"] == plan.get("selected_scenario")),
                None,
            )
            if selected:
                priority = "high" if selected["scenario_type"] == "combined_rehabilitation" else "moderate"
                result.append(DecisionRecommendation(
                    category="rehabilitation",
                    priority=priority,
                    title=f"Implement the feasible {selected['scenario_type'].replace('_', ' ')} scenario",
                    action=f"Use only the scenario's {len(selected.get('action_ids', []))} linked action(s), respecting the recorded budget, labor, timing, and field-confirmation controls.",
                    rationale=f"The scenario was selected from six alternatives with expected utility {float(selected['expected_utility']):.3f}, cost PHP {float(selected['total_cost_php']):,.2f}, and severe-loss probability {float(selected['severe_loss_probability']):.1%}.",
                    confidence=ConfidenceLevel.MODERATE,
                    source_components=["rehabilitation"],
                    evidence=[DecisionEvidence(
                        source_component="rehabilitation", source_engine=ENGINE_IDS["rehabilitation"],
                        record_id=str(payload.rehabilitation_plan_id), field="selected_scenario",
                        value=selected["scenario_type"], explanation="Highest-utility feasible scenario selected by the Phase 8 optimizer.",
                    )],
                    requires_field_confirmation=any(
                        action.get("requires_field_confirmation") and action.get("id") in set(selected.get("action_ids", []))
                        for action in plan.get("actions", [])
                    ),
                    limitations=["Scenario utility is comparative and is not guaranteed profit or guaranteed recovery."],
                ))
        return result

    @staticmethod
    def _overview(records, recommendations, requested_components, components) -> DecisionOverview:
        production = records["production"] or {}
        posterior = records.get("bayesian")
        pest_run = records.get("pest")
        intercrop_run = records.get("intercropping")
        plan = records.get("rehabilitation")
        distribution = posterior.get("production_distribution") if posterior else production.get("posterior")
        highest = max(pest_run.get("assessments", []), key=lambda item: item["outbreak_probability"], default=None) if pest_run else None
        eligible = [item for item in intercrop_run.get("assessments", []) if item.get("hard_constraint_passed")] if intercrop_run else []
        best = max(eligible, key=lambda item: item["suitability_score"], default=None)
        selected = None
        if plan:
            selected = next((item for item in plan.get("scenarios", []) if item["scenario_type"] == plan.get("selected_scenario")), None)
        succeeded_requested = sum(item.status == "succeeded" and item.component in requested_components for item in components)
        completeness = succeeded_requested / len(requested_components)
        return DecisionOverview(
            production_estimate=float(production.get("variety_adjusted_prediction") or production.get("raw_ml_prediction") or 0),
            production_unit=production.get("unit") or "tonne",
            production_lower=float(distribution["lower"]) if distribution else None,
            production_upper=float(distribution["upper"]) if distribution else None,
            probability_of_decline=float(posterior["probability_of_decline"]) if posterior else production.get("probability_of_decline"),
            probability_of_recovery=float(posterior["probability_of_recovery"]) if posterior else None,
            highest_pest_id=highest["pest_profile_id"] if highest else None,
            highest_pest_probability=float(highest["outbreak_probability"]) if highest else None,
            best_intercrop_id=best["candidate_id"] if best else None,
            best_intercrop_score=float(best["suitability_score"]) if best else None,
            selected_rehabilitation_scenario=plan.get("selected_scenario") if plan else None,
            selected_rehabilitation_cost_php=float(selected["total_cost_php"]) if selected else None,
            urgent_recommendation_count=sum(item.priority in {"high", "critical"} for item in recommendations),
            data_completeness=completeness,
        )

    @staticmethod
    def _traceability(components: list[DecisionComponentResult]) -> list[DecisionTraceEdge]:
        ids = {item.component: str(item.record_id) if item.record_id else None for item in components if item.status == "succeeded"}
        result: list[DecisionTraceEdge] = []
        for downstream, upstream_values in DEPENDENCY_GRAPH.items():
            if downstream not in ids:
                continue
            for upstream in upstream_values:
                if upstream in ids:
                    result.append(DecisionTraceEdge(
                        upstream_component=upstream,
                        downstream_component=downstream,
                        relationship=f"{downstream} consumes or conditions its interpretation on {upstream} output.",
                        upstream_record_id=ids[upstream],
                        downstream_record_id=ids[downstream],
                    ))
        for component in ids:
            if component != "production":
                result.append(DecisionTraceEdge(
                    upstream_component=component,
                    downstream_component="production",
                    relationship="The integrated decision record explains this component alongside the common production baseline; it does not overwrite the production model.",
                    upstream_record_id=ids[component],
                    downstream_record_id=ids["production"],
                ))
        return result

    @staticmethod
    def _weather_run_id(production: dict[str, Any]) -> UUID | None:
        provenance = production.get("provenance") or {}
        value = provenance.get("weather_run_id")
        return UUID(value) if value else None


decision_support_engine = DecisionSupportEngine()
from app.engines.registry import engine_registry  # noqa: E402
engine_registry.register(decision_support_engine)
