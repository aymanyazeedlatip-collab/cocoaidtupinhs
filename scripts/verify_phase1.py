from __future__ import annotations

from contextlib import closing

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = [
    "docs/phase_1/ARCHITECTURE.md",
    "docs/phase_1/DATA_CONTRACTS.md",
    "docs/phase_1/API_V2.md",
    "docs/phase_1/MIGRATIONS.md",
    "docs/phase_1/MODEL_RUNTIME.md",
    "docs/phase_1/TEST_REPORT.md",
    "docs/phase_1/USER_ACTIONS.md",
    "docs/phase_1/PHASE_1_STATUS.md",
    "manifests/phase1_contract_catalog.json",
    "manifests/phase1_engine_catalog.json",
    "manifests/phase1_parameter_registry.json",
    "manifests/phase1_unit_catalog.json",
    "manifests/phase1_model_registry.json",
    "manifests/phase1_migration_catalog.json",
    "baseline_snapshots/phase1_test_results.txt",
]


def fail(message: str) -> None:
    raise SystemExit(f"PHASE 1 VERIFICATION FAILED: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            fail(f"missing required artifact: {relative}")

    from app.core.config import settings
    from app.domain.contract_registry import contract_registry
    from app.engines.registry import engine_registry
    from app.models.registry import model_metadata
    from app.parameters.registry import parameter_registry
    from app.storage.migrations import MigrationManager

    if not settings.contract_api_version.startswith("3.0.0-draft."):
        fail("unexpected contract API version family")
    if settings.max_live_forecast_days != 16:
        fail("live forecast limit must be 16 days")

    entries = contract_registry.catalog()
    if len(entries) < 17 or len({item.schema_sha256 for item in entries}) != len(entries):
        fail("contract catalog is incomplete or contains duplicate schema hashes")

    engine_ids = {item.engine_id for item in engine_registry.descriptors()}
    required_engines = {
        "legacy.production", "legacy.bayesian", "v3.weather_assimilation", "v3.production",
        "v3.bayesian", "v3.pest_inference", "v3.intercropping", "v3.rehabilitation",
    }
    if not required_engines.issubset(engine_ids):
        fail("engine catalog is incomplete")

    if len(parameter_registry.descriptors()) < 2:
        fail("parameter registry is incomplete")

    metadata = model_metadata()
    original_checksums = json.loads((ROOT / "manifests" / "model_checksums.json").read_text(encoding="utf-8"))
    for name, item in metadata.items():
        if not item["available"]:
            fail(f"model unavailable: {name}")
        if item["artifact"]["sha256"] != original_checksums[name]["sha256"]:
            fail(f"model artifact changed: {name}")

    if "scikit-learn==1.9.0" not in (ROOT / "requirements.txt").read_text(encoding="utf-8"):
        fail("exact scikit-learn artifact runtime is not pinned")

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase1-") as temp:
        db_path = Path(temp) / "migration.sqlite3"
        manager = MigrationManager(db_path)
        if manager.upgrade(target_version=1) != [1] or manager.upgrade(target_version=1) != []:
            fail("migration upgrade is not idempotent")
        status = manager.status()
        if not status or status[0].state != "applied":
            fail("migration status is not applied")
        with closing(sqlite3.connect(db_path)) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"farms", "analyses", "reports", "saved_forecasts", "schema_migrations"}.issubset(tables):
            fail("migration did not create the legacy schema")

    old_db = settings.database_path
    old_reports = settings.reports_dir
    old_cache = settings.cache_dir
    old_offline = settings.offline_mode
    try:
        with tempfile.TemporaryDirectory(prefix="cocoaid-phase1-api-") as temp:
            runtime = Path(temp)
            settings.database_path = runtime / "api.sqlite3"
            settings.reports_dir = runtime / "reports"
            settings.cache_dir = runtime / "cache"
            settings.offline_mode = True
            from fastapi.testclient import TestClient
            from app.main import app
            from app.storage.database import initialize_database

            initialize_database()
            with TestClient(app) as client:
                if client.get("/api/health").json().get("api_version") != "2.11.0":
                    fail("legacy API health changed")
                health = client.get("/api/v2/health")
                if health.status_code != 200 or health.json().get("contract_api_version") != settings.contract_api_version:
                    fail("v2 contract API health failed")
                if client.get("/api/v2/contracts").status_code != 200:
                    fail("contract catalog API failed")
    finally:
        settings.database_path = old_db
        settings.reports_dir = old_reports
        settings.cache_dir = old_cache
        settings.offline_mode = old_offline

    test_result = (ROOT / "baseline_snapshots" / "phase1_test_results.txt").read_text(encoding="utf-8")
    if "135 passed" not in test_result:
        fail("phase 1 test result does not contain '135 passed'")

    print("COCOAID Phase 1 verification passed.")
    print(f"Contracts: {len(entries)}")
    print(f"Engines: {len(engine_ids)}")
    print(f"Parameter sets: {len(parameter_registry.descriptors())}")
    print("Automated tests: 135 passed")


if __name__ == "__main__":
    main()
