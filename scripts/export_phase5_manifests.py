from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bayesian.particle_filter import BAYESIAN_PARAMETER_VERSION, RELIABILITY_WEIGHTS, STATE_NAMES
from app.domain.contract_registry import contract_registry
from app.engines.bayesian import bayesian_engine
from app.main import app
from app.parameters.registry import parameter_registry
from app.storage.migrations.versions import MIGRATIONS

MANIFESTS = ROOT / "manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)


def write(name: str, value) -> None:
    (MANIFESTS / name).write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    write("phase5_migration_catalog.json", [{
        "version": item.version,
        "name": item.name,
        "checksum": item.checksum,
        "destructive_down": item.destructive_down,
    } for item in MIGRATIONS])
    write("phase5_engine_catalog.json", bayesian_engine.descriptor.model_dump(mode="json"))
    schema = app.openapi()
    paths = {path: methods for path, methods in schema["paths"].items() if path.startswith("/api/v2/bayesian")}
    write("phase5_endpoint_catalog.json", {
        "contract_api_version": "3.0.0-draft.5",
        "paths": paths,
    })
    contracts = [
        "BayesianEvidenceObservation", "BayesianSimulationRequest", "StatePosteriorInterval",
        "EvidenceAssimilationResult", "BayesianDiagnostics", "BayesianPosterior", "BayesianEngineOutput",
    ]
    write("phase5_contract_hashes.json", {
        name: contract_registry.entry(name).model_dump(mode="json") for name in contracts
    })
    descriptor = next(
        item for item in parameter_registry.descriptors()
        if item.parameter_set_id == "v3.bayesian_farm_state" and item.version == BAYESIAN_PARAMETER_VERSION
    )
    write("phase5_parameter_catalog.json", {
        "descriptor": descriptor.model_dump(mode="json"),
        "values": parameter_registry.values("v3.bayesian_farm_state", BAYESIAN_PARAMETER_VERSION),
        "evidence_reliability": {status.value: weight for status, weight in RELIABILITY_WEIGHTS.items()},
        "state_names": list(STATE_NAMES),
    })
    print("PHASE 5 MANIFESTS EXPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
