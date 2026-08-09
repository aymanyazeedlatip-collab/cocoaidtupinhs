from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.contract_registry import contract_registry
from app.engines.pest_inference import pest_inference_engine
from app.parameters.registry import parameter_registry
from app.pest.parameters import PEST_PARAMETER_SET_ID, PEST_PARAMETER_VERSION, SUPPORTED_PEST_IDS
from app.storage.migrations.versions import MIGRATIONS

OUT = ROOT / "manifests"
OUT.mkdir(exist_ok=True)


def write(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    contracts = [
        "PestObservation", "PestFarmContext", "PestAssessmentRequest",
        "PestEvidenceContribution", "PestManagementAction", "PestProfileAssessment",
        "PestAssessmentSummary", "PestEngineOutput",
    ]
    write("phase6_contract_hashes.json", {
        name: contract_registry.entry(name).model_dump(mode="json") for name in contracts
    })
    write("phase6_engine_catalog.json", pest_inference_engine.descriptor.model_dump(mode="json"))
    write("phase6_endpoint_catalog.json", {
        "contract_api_version": "3.0.0-draft.6",
        "endpoints": [
            "GET /api/v2/pests/status",
            "GET /api/v2/pests/profiles",
            "POST /api/v2/pests/observations",
            "GET /api/v2/pests/observations",
            "POST /api/v2/pests/assess",
            "GET /api/v2/pests/assessments",
            "GET /api/v2/pests/assessments/{assessment_id}",
        ],
    })
    write("phase6_migration_catalog.json", [
        {"version": item.version, "name": item.name, "checksum": item.checksum}
        for item in MIGRATIONS
    ])
    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == PEST_PARAMETER_SET_ID and item.version == PEST_PARAMETER_VERSION
    )
    write("phase6_parameter_catalog.json", descriptor.model_dump(mode="json"))
    write("phase6_pest_profile_catalog.json", {
        "supported_profile_ids": list(SUPPORTED_PEST_IDS),
        "profile_count": len(SUPPORTED_PEST_IDS),
        "taxonomy_boundary": "Asiatic palm weevil is not merged with legacy red palm weevil.",
    })
    print("PHASE 6 MANIFESTS EXPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
