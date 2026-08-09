from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coco_pilot.reports import FORMAL_REPORT_GENERATOR_VERSION
from app.coco_pilot.service import COCO_PILOT_ENGINE_VERSION, COCO_PILOT_PARAMETER_VERSION, COCO_PILOT_PROMPT_VERSION
from app.domain.contract_registry import contract_registry
from app.storage.migrations.versions import MIGRATIONS

OUT = ROOT / "manifests"
OUT.mkdir(exist_ok=True)


def write(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    contracts = [
        "CocoPilotRequest", "CocoPilotCitation", "CocoPilotRedactionSummary",
        "CocoPilotResponse", "FormalReportRequest", "FormalReportRecord",
    ]
    write("phase10_contract_hashes.json", {name: contract_registry.entry(name).model_dump(mode="json") for name in contracts})
    write("phase10_service_catalog.json", {
        "service_id": "v3.coco_pilot",
        "version": COCO_PILOT_ENGINE_VERSION,
        "parameter_version": COCO_PILOT_PARAMETER_VERSION,
        "prompt_version": COCO_PILOT_PROMPT_VERSION,
        "formal_report_generator_version": FORMAL_REPORT_GENERATOR_VERSION,
        "providers": ["deterministic", "gemini_if_configured"],
        "formats": ["docx", "pdf"],
    })
    write("phase10_endpoint_catalog.json", {
        "contract_api_version": "3.0.0-draft.10",
        "endpoints": [
            "GET /api/v2/coco-pilot/status", "POST /api/v2/coco-pilot/explain",
            "GET /api/v2/coco-pilot/runs", "GET /api/v2/coco-pilot/runs/{run_id}",
            "POST /api/v2/formal-reports/generate", "GET /api/v2/formal-reports",
            "GET /api/v2/formal-reports/{report_id}", "GET /api/v2/formal-reports/{report_id}/download",
        ],
    })
    write("phase10_migration_catalog.json", [{"version": item.version, "name": item.name, "checksum": item.checksum} for item in MIGRATIONS])
    print("PHASE 10 MANIFESTS EXPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
