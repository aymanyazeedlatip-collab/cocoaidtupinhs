from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.contract_registry import contract_registry
from app.engines.intercropping import intercropping_engine
from app.intercropping.catalog import load_requirement_catalog
from app.intercropping.parameters import (
    INTERCROP_PARAMETER_SET_ID,
    INTERCROP_PARAMETER_VERSION,
    INTERCROP_REQUIREMENT_PROFILE_VERSION,
)
from app.parameters.registry import parameter_registry
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
        "IntercropCellContext",
        "IntercropAssessmentRequest",
        "CanopyLightEstimate",
        "IntercropEconomicPotential",
        "IntercropCandidateSnapshot",
        "IntercropCandidateAssessment",
        "IntercropEngineSummary",
        "IntercropEngineOutput",
        "SuitabilityComponent",
    ]
    write("phase7_contract_hashes.json", {
        name: contract_registry.entry(name).model_dump(mode="json") for name in contracts
    })
    write("phase7_engine_catalog.json", intercropping_engine.descriptor.model_dump(mode="json"))
    write("phase7_endpoint_catalog.json", {
        "contract_api_version": "3.0.0-draft.7",
        "endpoints": [
            "GET /api/v2/intercropping/status",
            "GET /api/v2/intercropping/candidates",
            "POST /api/v2/intercropping/assess",
            "GET /api/v2/intercropping/assessments",
            "GET /api/v2/intercropping/assessments/{assessment_id}",
        ],
    })
    write("phase7_migration_catalog.json", [
        {"version": item.version, "name": item.name, "checksum": item.checksum}
        for item in MIGRATIONS
    ])
    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == INTERCROP_PARAMETER_SET_ID
        and item.version == INTERCROP_PARAMETER_VERSION
    )
    write("phase7_parameter_catalog.json", descriptor.model_dump(mode="json"))
    catalog = load_requirement_catalog()
    encoded = json.dumps(catalog, sort_keys=True, separators=(",", ":")).encode("utf-8")
    write("phase7_requirement_catalog.json", {
        "profile_version": catalog["profile_version"],
        "expected_profile_version": INTERCROP_REQUIREMENT_PROFILE_VERSION,
        "candidate_count": len(catalog["profiles"]),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "economic_profile_candidates": sorted(
            item["candidate_id"] for item in catalog["profiles"]
            if item.get("economic_profile_crop")
        ),
        "notice": catalog["notice"],
    })
    print("PHASE 7 MANIFESTS EXPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
