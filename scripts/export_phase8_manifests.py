from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.contract_registry import contract_registry
from app.engines.rehabilitation import rehabilitation_engine
from app.parameters.registry import parameter_registry
from app.rehabilitation.parameters import (
    REHABILITATION_COST_CATALOG_VERSION,
    REHABILITATION_PARAMETER_SET_ID,
    REHABILITATION_PARAMETER_VERSION,
)
from app.storage.migrations.versions import MIGRATIONS

OUT = ROOT / "manifests"
OUT.mkdir(exist_ok=True)


def write(name: str, payload) -> None:
    (OUT / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    contracts = [
        "CostEstimate", "RehabilitationTrigger", "RehabilitationCellContext",
        "RehabilitationPlanRequest", "RehabilitationAction",
        "RehabilitationScenarioResult", "RehabilitationPlan",
        "RehabilitationEngineSummary", "RehabilitationEngineOutput",
    ]
    write("phase8_contract_hashes.json", {
        name: contract_registry.entry(name).model_dump(mode="json") for name in contracts
    })
    write("phase8_engine_catalog.json", rehabilitation_engine.descriptor.model_dump(mode="json"))
    write("phase8_endpoint_catalog.json", {
        "contract_api_version": "3.0.0-draft.10",
        "endpoints": [
            "GET /api/v2/rehabilitation/status",
            "POST /api/v2/rehabilitation/plan",
            "GET /api/v2/rehabilitation/plans",
            "GET /api/v2/rehabilitation/plans/{plan_id}",
        ],
    })
    write("phase8_migration_catalog.json", [
        {"version": item.version, "name": item.name, "checksum": item.checksum}
        for item in MIGRATIONS
    ])
    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == REHABILITATION_PARAMETER_SET_ID
        and item.version == REHABILITATION_PARAMETER_VERSION
    )
    payload = descriptor.model_dump(mode="json")
    payload["cost_catalog_version"] = REHABILITATION_COST_CATALOG_VERSION
    write("phase8_parameter_catalog.json", payload)
    print("PHASE 8 MANIFESTS EXPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
