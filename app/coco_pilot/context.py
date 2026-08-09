from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from app.data_foundation import repository as data_repository
from app.decision_support import repository as decision_repository
from app.rehabilitation import repository as rehabilitation_repository

_PII_KEYS = {
    "farmer_name", "owner_name", "full_name", "first_name", "middle_name", "last_name",
    "email", "email_address", "phone", "phone_number", "mobile", "contact_number",
    "street_address", "address", "national_id", "identity_fingerprint", "raw_payload",
}
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?63|0)?9\d{9}(?!\d)")


def redact_payload(value: Any) -> tuple[Any, int]:
    removed = 0

    def walk(item: Any) -> Any:
        nonlocal removed
        if isinstance(item, dict):
            result: dict[str, Any] = {}
            for key, child in item.items():
                normalized = str(key).strip().lower()
                if normalized in _PII_KEYS or normalized.endswith("_farmer_name"):
                    removed += 1
                    continue
                result[str(key)] = walk(child)
            return result
        if isinstance(item, list):
            return [walk(child) for child in item]
        if isinstance(item, str):
            cleaned, email_count = _EMAIL_RE.subn("[REDACTED EMAIL]", item)
            cleaned, phone_count = _PHONE_RE.subn("[REDACTED PHONE]", cleaned)
            removed += email_count + phone_count
            return cleaned
        return item

    return walk(copy.deepcopy(value)), removed


def _source_manifest(decision: dict[str, Any], *, database_path: Path | None = None) -> tuple[list[dict[str, Any]], int]:
    manifest: list[dict[str, Any]] = [{
        "source_type": "decision_support_run",
        "source_id": str(decision["analysis_run_id"]),
        "title": "COCOAID integrated decision-support record",
        "access_class": "analytical",
    }]
    for component in decision.get("component_results", []):
        if component.get("record_id"):
            manifest.append({
                "source_type": "analytical_component",
                "source_id": str(component["record_id"]),
                "title": f"{component.get('component', 'unknown').title()} analytical output",
                "engine_id": component.get("engine_id"),
                "status": component.get("status"),
                "access_class": "analytical",
            })

    public_documents = data_repository.list_source_documents(include_restricted=False, database_path=database_path)
    all_documents = data_repository.list_source_documents(include_restricted=True, database_path=database_path)
    restricted_excluded = max(0, len(all_documents) - len(public_documents))

    overview = decision.get("overview", {})
    highest_pest = overview.get("highest_pest_id")
    best_intercrop = overview.get("best_intercrop_id")

    relevant_titles: set[str] = set()
    if highest_pest:
        for pest in data_repository.list_pests(database_path=database_path):
            if pest.get("id") == highest_pest:
                relevant_titles.add(str(pest.get("source_title") or ""))
    if best_intercrop:
        for crop in data_repository.list_intercrops(database_path=database_path):
            if crop.get("id") == best_intercrop:
                relevant_titles.add(str(crop.get("source_title") or ""))

    for document in public_documents:
        if relevant_titles and document.get("title") not in relevant_titles:
            continue
        manifest.append({
            "source_type": "PCA_reference",
            "source_id": document["id"],
            "title": document["title"],
            "organization": document.get("organization"),
            "category": document.get("category"),
            "sha256": document.get("sha256"),
            "access_class": document.get("access_class"),
        })
    return manifest, restricted_excluded


def build_context(analysis_run_id: UUID, *, database_path: Path | None = None) -> dict[str, Any]:
    decision = decision_repository.get_run(analysis_run_id, database_path=database_path)
    if not decision:
        raise FileNotFoundError("Decision-support run was not found.")
    redacted, removed = redact_payload(decision)
    linked_records: dict[str, Any] = {}
    plan_id = decision.get("rehabilitation_plan_id")
    if plan_id:
        plan = rehabilitation_repository.get_plan(plan_id, database_path=database_path)
        if plan:
            redacted_plan, plan_removed = redact_payload(plan)
            linked_records["rehabilitation_plan"] = redacted_plan
            removed += plan_removed
    manifest, restricted_excluded = _source_manifest(redacted, database_path=database_path)
    return {
        "decision": redacted,
        "linked_records": linked_records,
        "source_manifest": manifest,
        "redaction_summary": {
            "pii_fields_removed": removed,
            "restricted_sources_excluded": restricted_excluded,
            "raw_farmer_records_included": False,
            "farmer_names_included": False,
        },
    }
