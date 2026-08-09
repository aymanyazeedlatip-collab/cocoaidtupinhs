from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.decision_support.parameters import (
    DECISION_SUPPORT_PARAMETER_SET_ID, DECISION_SUPPORT_PARAMETER_VERSION,
    DEPENDENCY_GRAPH, DEPENDENCY_GRAPH_VERSION,
)
from app.domain.contract_registry import contract_registry
from app.engines.decision_support import decision_support_engine
from app.parameters.registry import parameter_registry
from app.storage.migrations.versions import MIGRATIONS

OUT = ROOT / "manifests"
OUT.mkdir(exist_ok=True)


def write(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    contracts = [
        "DecisionSupportRequest", "DecisionComponentResult", "DecisionEvidence",
        "DecisionRecommendation", "DecisionTraceEdge", "DecisionOverview",
        "DecisionSupportRecord", "DecisionSupportSummary", "DecisionSupportEngineOutput",
    ]
    write("phase9_contract_hashes.json", {name: contract_registry.entry(name).model_dump(mode="json") for name in contracts})
    write("phase9_engine_catalog.json", decision_support_engine.descriptor.model_dump(mode="json"))
    write("phase9_endpoint_catalog.json", {
        "contract_api_version": "3.0.0-draft.10",
        "endpoints": [
            "GET /api/v2/decision-support/status",
            "POST /api/v2/decision-support/compose",
            "GET /api/v2/decision-support/runs",
            "GET /api/v2/decision-support/runs/{analysis_run_id}",
        ],
    })
    write("phase9_migration_catalog.json", [{"version": item.version, "name": item.name, "checksum": item.checksum} for item in MIGRATIONS])
    descriptor = next(item for item in parameter_registry.descriptors() if item.parameter_set_id == DECISION_SUPPORT_PARAMETER_SET_ID and item.version == DECISION_SUPPORT_PARAMETER_VERSION)
    payload = descriptor.model_dump(mode="json")
    payload["dependency_graph_version"] = DEPENDENCY_GRAPH_VERSION
    payload["dependency_graph"] = DEPENDENCY_GRAPH
    write("phase9_parameter_catalog.json", payload)
    print("PHASE 9 MANIFESTS EXPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
