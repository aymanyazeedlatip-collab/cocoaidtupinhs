from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.contract_registry import contract_registry
from app.engines.production import production_engine
from app.main import app
from app.models.registry import model_metadata
from app.production.feature_adapter import LEGACY_PRODUCTION_FEATURE_ORDER, PRODUCTION_FEATURE_ADAPTER_VERSION
from app.storage.migrations.versions import MIGRATIONS

MANIFESTS = ROOT / "manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)


def write(name: str, value) -> None:
    (MANIFESTS / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    production = model_metadata("production")["production"]
    write("phase4_feature_schema.json", {
        "feature_adapter_version": PRODUCTION_FEATURE_ADAPTER_VERSION,
        "feature_order": LEGACY_PRODUCTION_FEATURE_ORDER,
        "feature_count": len(LEGACY_PRODUCTION_FEATURE_ORDER),
        "artifact_feature_order_matches": production["features"] == LEGACY_PRODUCTION_FEATURE_ORDER,
    })
    write("phase4_migration_catalog.json", [{
        "version": item.version,
        "name": item.name,
        "checksum": item.checksum,
        "destructive_down": item.destructive_down,
    } for item in MIGRATIONS])
    write("phase4_engine_catalog.json", production_engine.descriptor.model_dump(mode="json"))
    schema = app.openapi()
    phase4_paths = {
        path: methods for path, methods in schema["paths"].items()
        if path.startswith("/api/v2/production") or path == "/api/v2/data-foundation/intercrop-income-assessment"
    }
    write("phase4_endpoint_catalog.json", {
        "contract_api_version": "3.0.0-draft.4",
        "paths": phase4_paths,
    })
    phase4_contracts = [
        "ProductionEngineRequest", "LegacyProductionFeatureSnapshot", "ProductEstimate",
        "ProductionShadowComparison", "ProductionEngineOutput", "ProductionActualInput", "ProductionForecast",
    ]
    write("phase4_contract_hashes.json", {
        name: contract_registry.entry(name).model_dump(mode="json") for name in phase4_contracts
    })
    write("phase4_model_artifact.json", {
        "available": production["available"],
        "version": production["version"],
        "features": production["features"],
        "card": production["card"],
        "artifact": production["artifact"],
        "required_runtime": production["artifact"]["serialized_runtime"],
    })

    assessment = json.loads((ROOT / "data" / "reference" / "intercrop_income_assessment.json").read_text(encoding="utf-8"))
    write("phase4_intercrop_income_assessment.json", {
        "assessment_version": assessment["assessment_version"],
        "source_sha256": assessment["source_sha256"],
        "intercrop_record_count": assessment["intercrop_record_count"],
        "crop_profiles": assessment["crop_profiles"],
        "site_profile_count": len(assessment["site_profiles"]),
        "quality_findings": assessment["quality_findings"],
        "approved_uses": assessment["approved_uses"],
        "prohibited_or_deferred_uses": assessment["prohibited_or_deferred_uses"],
    })
    raw = ROOT / "data_sources" / "raw" / "intercropping" / "Income_Assessment_RXII_2024.xlsx"
    write("phase4_source_checksums.json", {
        "data_sources/raw/intercropping/Income_Assessment_RXII_2024.xlsx": sha256(raw),
        "artifacts/models/production_model.joblib": sha256(ROOT / "artifacts" / "models" / "production_model.joblib"),
    })
    print("PHASE 4 MANIFESTS EXPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
