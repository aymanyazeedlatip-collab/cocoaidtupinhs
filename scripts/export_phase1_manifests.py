from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.domain.contract_registry import contract_registry
from app.domain.units import CANONICAL_VARIABLE_UNITS, UNIT_CATALOG
from app.engines.registry import engine_registry
from app.models.registry import MODEL_SERIALIZATION_RUNTIME, model_metadata, model_runtime_status
from app.parameters.registry import parameter_registry
from app.storage.migrations import MIGRATIONS


def write(name: str, payload: object) -> None:
    path = ROOT / "manifests" / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def main() -> None:
    write(
        "phase1_contract_catalog.json",
        {
            "contract_api_version": settings.contract_api_version,
            "contracts": [item.model_dump(mode="json") for item in contract_registry.catalog()],
        },
    )
    write(
        "phase1_engine_catalog.json",
        {"engines": [item.model_dump(mode="json") for item in engine_registry.descriptors()]},
    )
    write(
        "phase1_parameter_registry.json",
        {"parameter_sets": [item.model_dump(mode="json") for item in parameter_registry.descriptors()]},
    )
    write(
        "phase1_unit_catalog.json",
        {
            "units": [UNIT_CATALOG[key].model_dump(mode="json") for key in sorted(UNIT_CATALOG, key=lambda item: item.value)],
            "canonical_variable_units": {key: value.value for key, value in sorted(CANONICAL_VARIABLE_UNITS.items())},
        },
    )
    write(
        "phase1_model_registry.json",
        {
            "serialized_runtime": MODEL_SERIALIZATION_RUNTIME,
            "build_runtime_status": model_runtime_status(),
            "models": model_metadata(),
        },
    )
    write(
        "phase1_migration_catalog.json",
        {
            "migrations": [
                {
                    "version": item.version,
                    "name": item.name,
                    "checksum": item.checksum,
                    "reversible": item.down is not None,
                    "destructive_down": item.destructive_down,
                }
                for item in MIGRATIONS
            ]
        },
    )
    print("Phase 1 manifests exported.")


if __name__ == "__main__":
    main()
