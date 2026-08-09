from __future__ import annotations

from contextlib import closing
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.domain.enums import EngineAvailability
from app.engines.weather_assimilation import weather_assimilation_engine
from app.storage.migrations import MigrationManager
from app.weather.assimilation.features import FEATURE_ADAPTER_VERSION, build_weather_feature_set
from app.weather.assimilation.normalizer import live_only_payload, normalize_open_meteo_payload
from app.weather.assimilation.repository import compare_runs, get_feature_set_for_run, get_run, save_run
from tests.weather_factory import RETRIEVED_AT, make_open_meteo_payload

REQUIRED_ARTIFACTS = [
    "docs/phase_3/ARCHITECTURE.md",
    "docs/phase_3/WEATHER_RUN_SCHEMA.md",
    "docs/phase_3/FEATURE_ADAPTER.md",
    "docs/phase_3/LIVE_WEATHER_BOUNDARY.md",
    "docs/phase_3/CACHE_AND_FAILURE_BEHAVIOR.md",
    "docs/phase_3/API.md",
    "docs/phase_3/TEST_REPORT.md",
    "docs/phase_3/USER_ACTIONS.md",
    "docs/phase_3/PHASE_3_STATUS.md",
    "docs/phase_3/RELEASE_NOTES.md",
    "manifests/phase3_migration_catalog.json",
    "manifests/phase3_weather_feature_catalog.json",
    "manifests/phase3_endpoint_catalog.json",
    "manifests/phase3_contract_hashes.json",
    "manifests/phase3_engine_catalog.json",
    "baseline_snapshots/phase3_test_results.txt",
]


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 3 artifact: {relative}"
    assert settings.contract_api_version == "3.0.0-draft.10"
    assert settings.max_live_forecast_days == 16
    assert weather_assimilation_engine.descriptor.availability == EngineAvailability.AVAILABLE
    assert weather_assimilation_engine.descriptor.version == "1.0.0"

    payload = make_open_meteo_payload()
    normalized = normalize_open_meteo_payload(
        payload, model="auto", forecast_days=16, history_days=90, retrieved_at=RETRIEVED_AT,
    )
    live = live_only_payload(payload, forecast_days=16, retrieved_at=RETRIEVED_AT)
    assert len(live["daily"]["time"]) == 16
    assert live["historical_values_included"] is False
    assert {item.period_kind for item in normalized.values} == {"historical", "current", "forecast"}
    assert normalized.provider_run_at is None
    features = build_weather_feature_set(normalized)
    assert features.feature_adapter_version == FEATURE_ADAPTER_VERSION
    assert len(features.features) == 14

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase3-") as temp:
        database = Path(temp) / "phase3.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=3) == [1, 2, 3]
        assert manager.upgrade(target_version=3) == []
        with closing(sqlite3.connect(database)) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            conn.execute("PRAGMA foreign_keys=ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

        first_id, feature_id, reused = save_run(normalized, features, database_path=database)
        assert reused is False and feature_id
        duplicate_id, _, duplicate = save_run(
            normalized, build_weather_feature_set(normalized), database_path=database,
        )
        assert duplicate is True and duplicate_id == first_id
        first = get_run(first_id, include_values=True, database_path=database)
        assert first and first["values"]
        stored_features = get_feature_set_for_run(first_id, database_path=database)
        assert stored_features and len(stored_features["features"]) == 14

        changed = normalize_open_meteo_payload(
            make_open_meteo_payload(forecast_rain_adjustment=1.0), model="auto",
            forecast_days=16, history_days=90, retrieved_at=RETRIEVED_AT,
        )
        second_id, _, _ = save_run(changed, build_weather_feature_set(changed), database_path=database)
        comparison = compare_runs(first_id, second_id, database_path=database)
        assert comparison["metrics"]["precipitation_sum"]["mean_change"] == 1.0

    frontend = (ROOT / "app" / "static" / "weather-viewer" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "app" / "static" / "weather-viewer" / "index.html").read_text(encoding="utf-8")
    assert "384-hour (16-day)" in frontend
    assert "16-day outlook" in html
    assert "10-day outlook" not in html

    test_result = (ROOT / "baseline_snapshots" / "phase3_test_results.txt").read_text(encoding="utf-8")
    assert "169 passed" in test_result
    assert "warning" not in test_result.lower()
    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": [1, 2, 3],
        "weather_engine": weather_assimilation_engine.descriptor.engine_id,
        "feature_adapter_version": FEATURE_ADAPTER_VERSION,
        "feature_count": len(features.features),
        "live_forecast_days": len(live["daily"]["time"]),
    }, indent=2))
    print("PHASE 3 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
