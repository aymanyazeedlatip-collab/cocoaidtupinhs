from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.coco_pilot.context import build_context
from app.coco_pilot import repository
from app.domain.coco_pilot import (
    CocoPilotCitation,
    CocoPilotRedactionSummary,
    CocoPilotRequest,
    CocoPilotResponse,
)
from app.services.assistant import assistant_status, chat_with_gemini

COCO_PILOT_ENGINE_VERSION = "1.0.0"
COCO_PILOT_PARAMETER_VERSION = "coco-pilot-grounding-parameters-1.0.0"
COCO_PILOT_PROMPT_VERSION = "coco-pilot-structured-prompt-1.0.0"

_LIMITATIONS = [
    "CoCO-PILOT explains saved analytical outputs; it does not create new field evidence.",
    "Pest-risk results are not laboratory diagnoses and do not authorize unverified chemical dosage.",
    "Intercrop income values are gross-revenue scenarios, not guaranteed net profit.",
    "Long-term climate-conditioned paths are scenarios, not exact weather forecasts.",
]


def _percent(value: Any) -> str:
    return "not available" if value is None else f"{float(value):.1%}"


def _number(value: Any, digits: int = 2) -> str:
    return "not available" if value is None else f"{float(value):,.{digits}f}"


def _component(decision: dict[str, Any], name: str) -> dict[str, Any]:
    return next((item for item in decision.get("component_results", []) if item.get("component") == name), {})


def _citations(decision: dict[str, Any], manifest: list[dict[str, Any]]) -> list[CocoPilotCitation]:
    result: list[CocoPilotCitation] = []
    seen: set[tuple[str, str, str]] = set()
    index = 1
    for recommendation in decision.get("recommendations", []):
        for evidence in recommendation.get("evidence", []):
            key = (str(evidence.get("record_id")), str(evidence.get("field")), str(evidence.get("value")))
            if key in seen:
                continue
            seen.add(key)
            result.append(CocoPilotCitation(
                citation_id=f"C{index}",
                source_type="analytical_output",
                source_id=str(evidence.get("record_id")),
                title=f"{str(evidence.get('source_component', 'unknown')).title()} analytical result",
                source_field=str(evidence.get("field")),
                claim=str(evidence.get("explanation") or recommendation.get("rationale") or "Stored analytical evidence."),
            ))
            index += 1
    for source in manifest:
        if source.get("source_type") != "PCA_reference":
            continue
        result.append(CocoPilotCitation(
            citation_id=f"C{index}", source_type="PCA_reference",
            source_id=str(source.get("source_id")), title=str(source.get("title")),
            claim="Official reference material used to contextualize the linked pest or intercropping output.",
        ))
        index += 1
    return result[:80]


def _priority_recommendations(decision: dict[str, Any]) -> list[dict[str, Any]]:
    order = {"critical": 5, "high": 4, "moderate": 3, "low": 2, "routine": 1}
    return sorted(
        decision.get("recommendations", []),
        key=lambda item: (-order.get(str(item.get("priority")), 0), str(item.get("category"))),
    )


def _deterministic_content(
    mode: str, decision: dict[str, Any], linked_records: dict[str, Any], question: str | None
) -> tuple[str, list[str], str]:
    overview = decision.get("overview", {})
    recommendations = _priority_recommendations(decision)
    production = _component(decision, "production").get("summary", {})
    bayesian = _component(decision, "bayesian").get("summary", {})
    pest = _component(decision, "pest").get("summary", {})
    intercrop = _component(decision, "intercropping").get("summary", {})
    rehabilitation = _component(decision, "rehabilitation").get("summary", {})

    estimate = overview.get("production_estimate")
    unit = overview.get("production_unit", "tonnes")
    completeness = _percent(overview.get("data_completeness"))
    top_pest = overview.get("highest_pest_id")
    top_pest_probability = overview.get("highest_pest_probability")
    best_crop = overview.get("best_intercrop_id")
    best_score = overview.get("best_intercrop_score")
    selected_scenario = overview.get("selected_rehabilitation_scenario")
    rehabilitation_plan = linked_records.get("rehabilitation_plan") or {}
    scenarios = list(rehabilitation_plan.get("scenarios") or [])
    actions = list(rehabilitation_plan.get("actions") or [])

    if mode == "risk_summary":
        conclusion = (
            f"The integrated record is {completeness} complete. The highest stored pest risk is "
            f"{top_pest or 'not available'} at {_percent(top_pest_probability)}, while the Bayesian decline "
            f"probability is {_percent(overview.get('probability_of_decline'))}."
        )
        bullets = [
            f"Production baseline: {_number(estimate, 3)} {unit}.",
            f"Bayesian recovery probability: {_percent(overview.get('probability_of_recovery'))}.",
            f"Urgent recommendation count: {int(overview.get('urgent_recommendation_count') or 0)}.",
            "Conditional pest loss and expected pest loss remain separate in the source assessment.",
        ]
        action = "Verify the highest-priority risk in the field before irreversible treatment."
    elif mode == "uncertainty":
        distribution = bayesian.get("production_distribution") or {}
        conclusion = (
            f"The production baseline is {_number(estimate, 3)} {unit}. Where a Bayesian posterior is available, "
            f"the stored interval is {_number(distribution.get('lower'), 3)} to {_number(distribution.get('upper'), 3)} {unit}."
        )
        bullets = [
            f"Probability of decline: {_percent(overview.get('probability_of_decline'))}.",
            f"Probability of recovery: {_percent(overview.get('probability_of_recovery'))}.",
            f"Data completeness: {completeness}.",
            "The interval is conditional on entered farm state, confirmed evidence, and versioned parameters.",
        ]
        action = "Collect actual harvest, palm-condition, and pest observations to reduce posterior uncertainty."
    elif mode == "compare_scenarios":
        selected_result = rehabilitation.get("selected_scenario_result") or {}
        conclusion = (
            f"The stored optimizer selected {str(selected_scenario or 'no selected scenario').replace('_', ' ')} "
            f"after retaining no action as a mandatory comparator."
        )
        if scenarios:
            scenario_order = {"no_action": 0, "pest_management": 1, "fertilization": 2, "replanting": 3, "intercropping": 4, "combined_rehabilitation": 5}
            ordered = sorted(scenarios, key=lambda item: scenario_order.get(str(item.get("scenario_type")), 99))
            bullets = [
                f"{str(item.get('scenario_type') or 'unknown').replace('_', ' ').title()}: "
                f"{item.get('status', 'unknown')}, PHP {_number(item.get('total_cost_php'), 2)}, "
                f"utility {_number(item.get('expected_utility'), 3)}, severe-loss probability {_percent(item.get('severe_loss_probability'))}."
                for item in ordered[:6]
            ]
        else:
            bullets = [
                f"Selected cost: PHP {_number(selected_result.get('total_cost_php'), 2)}.",
                f"Selected labor: {_number(selected_result.get('labor_person_days'), 1)} person-days.",
                f"Selected severe-loss probability: {_percent(selected_result.get('severe_loss_probability'))}.",
                f"Selected expected utility: {_number(selected_result.get('expected_utility'), 3)}.",
            ]
        action = "Review scenario feasibility, linked action IDs, budget, labor, and field-confirmation requirements before implementation."
    elif mode == "work_plan":
        conclusion = (
            f"The current plan is centered on {str(selected_scenario or 'the saved feasible scenario').replace('_', ' ')} "
            f"and contains {int(rehabilitation.get('action_count') or len(actions))} candidate actions."
        )
        selected_record = next((item for item in scenarios if item.get("scenario_type") == selected_scenario), {})
        selected_action_ids = {str(item) for item in selected_record.get("action_ids", [])}
        selected_actions = [item for item in actions if str(item.get("id") or item.get("action_id")) in selected_action_ids]
        selected_actions.sort(key=lambda item: (-int(item.get("priority") or 0), str(item.get("scheduled_date") or "")))
        if selected_actions:
            bullets = [
                f"{str(item.get('action_type') or 'action').replace('_', ' ').title()}: "
                f"{item.get('problem_detected') or 'stored rehabilitation need'}; scheduled {item.get('scheduled_date') or 'after verification'}; "
                f"cost PHP {_number(item.get('total_php'), 2)}."
                for item in selected_actions[:5]
            ]
            bullets.append("Record completed work and confirmed outcomes so the Bayesian state can be updated later.")
        else:
            bullets = [
                f"First priority: {recommendations[0].get('action') if recommendations else 'Inspect the farm and record evidence.'}",
                f"Highest pest to inspect: {top_pest or 'not available'} ({_percent(top_pest_probability)}).",
                f"Best current intercrop candidate: {best_crop or 'not available'} ({_number(best_score, 1)}/100).",
                "Record completed work and confirmed outcomes so the Bayesian state can be updated later.",
            ]
        action = "Start with field verification, then execute only actions linked to the selected feasible scenario."
    elif mode == "report_narrative":
        conclusion = (
            f"COCOAID estimates a current production baseline of {_number(estimate, 3)} {unit} and integrates "
            f"Bayesian uncertainty, pest inference, intercropping suitability, and rehabilitation planning in one traceable record."
        )
        bullets = [
            f"Highest pest-risk profile: {top_pest or 'not available'} at {_percent(top_pest_probability)}.",
            f"Highest acceptable intercrop: {best_crop or 'not available'} at {_number(best_score, 1)}/100.",
            f"Selected rehabilitation scenario: {str(selected_scenario or 'not available').replace('_', ' ')}.",
            f"The integrated record is {completeness} complete and preserves versioned source identifiers.",
        ]
        action = "Use this narrative with the numeric tables and provenance appendix; do not treat it as independent evidence."
    else:
        conclusion = (
            f"COCOAID's integrated record uses {_number(estimate, 3)} {unit} as the production baseline and "
            f"links it to {len(decision.get('recommendations', []))} traceable recommendation(s)."
        )
        bullets = [
            f"Highest pest risk: {top_pest or 'not available'} at {_percent(top_pest_probability)}.",
            f"Best hard-constraint-passing intercrop: {best_crop or 'not available'} at {_number(best_score, 1)}/100.",
            f"Selected rehabilitation scenario: {str(selected_scenario or 'not available').replace('_', ' ')}.",
            f"Data completeness: {completeness}; partial components remain disclosed rather than fabricated.",
        ]
        if question:
            bullets.append(f"User focus: {question.strip()[:500]}")
        action = recommendations[0].get("action") if recommendations else "Verify current farm conditions before taking action."
    return conclusion, bullets[:6], action


def _full_text(conclusion: str, bullets: list[str], action_line: str, citations: list[CocoPilotCitation]) -> str:
    lines = [conclusion]
    for index, bullet in enumerate(bullets, start=1):
        marker = f" [C{index}]" if index <= len(citations) else ""
        lines.append(f"- {bullet}{marker}")
    lines.append(f"Action: {action_line}")
    if citations:
        lines.append("Sources:")
        for citation in citations:
            field = f", field {citation.source_field}" if citation.source_field else ""
            page = f", page {citation.source_page}" if citation.source_page else ""
            lines.append(f"[{citation.citation_id}] {citation.title} ({citation.source_type}{field}{page}).")
    return "\n".join(lines)[:16000]


def _digits(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text))


def _safe_ai_answer(answer: str, deterministic_text: str) -> bool:
    if not answer.strip() or len(answer) > 12000:
        return False
    prohibited = re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|ml|g|kg)\s*(?:/|per)\s*(?:l|liter|tree|palm)\b", answer, re.I)
    if prohibited:
        return False
    return _digits(answer).issubset(_digits(deterministic_text))


class CocoPilotService:
    async def explain(self, request: CocoPilotRequest, *, database_path: Path | None = None) -> CocoPilotResponse:
        context = build_context(request.analysis_run_id, database_path=database_path)
        decision = context["decision"]
        citations = _citations(decision, context["source_manifest"] if request.include_pca_references else [])
        conclusion, bullets, action_line = _deterministic_content(request.mode, decision, context["linked_records"], request.question)
        deterministic_text = _full_text(conclusion, bullets, action_line, citations)
        provider = "deterministic"
        provider_model = None
        status = "completed"
        warnings = list(decision.get("warnings", []))
        full_text = deterministic_text

        if request.provider_mode == "gemini_if_configured":
            provider_state = assistant_status()
            if provider_state.get("configured"):
                prompt = (
                    "Rewrite the supplied deterministic COCOAID explanation for clarity. Preserve every numeric value, "
                    "do not add facts, do not add chemical dosage, retain uncertainty, and keep the Sources section.\n\n"
                    + deterministic_text
                )
                try:
                    result = await chat_with_gemini(
                        prompt, history=[],
                        context={"rehabilitation_plan": {
                            "decision_support": decision,
                            "linked_records": context["linked_records"],
                            "source_manifest": context["source_manifest"],
                        }},
                        document_ids=[],
                    )
                    candidate = str(result.get("answer") or "")
                    if _safe_ai_answer(candidate, deterministic_text):
                        full_text = candidate
                        provider = "google_ai"
                        provider_model = str(result.get("model") or "Automatic compatible Flash model")
                    else:
                        status = "completed_with_fallback"
                        warnings.append("AI narrative failed deterministic numeric or safety validation; deterministic text was retained.")
                except Exception as exc:
                    status = "completed_with_fallback"
                    warnings.append(f"AI narrative was unavailable; deterministic text was retained. {str(exc)[:300]}")
            else:
                status = "completed_with_fallback"
                warnings.append("Google AI is not configured; deterministic grounded explanation was generated.")

        response = CocoPilotResponse(
            analysis_run_id=request.analysis_run_id,
            mode=request.mode,
            provider=provider,
            provider_model=provider_model,
            status=status,
            conclusion=conclusion,
            bullets=bullets,
            action_line=action_line,
            full_text=full_text,
            citations=citations,
            source_manifest=context["source_manifest"] if request.include_pca_references else [
                item for item in context["source_manifest"] if item.get("source_type") != "PCA_reference"
            ],
            redaction_summary=CocoPilotRedactionSummary.model_validate(context["redaction_summary"]),
            warnings=warnings[:50],
            limitations=_LIMITATIONS,
            created_at=request.generated_at.astimezone(UTC),
        )
        repository.save_response(response, database_path=database_path)
        return response


coco_pilot_service = CocoPilotService()
