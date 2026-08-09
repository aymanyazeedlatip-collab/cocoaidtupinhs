from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.data_foundation.repository import intercrop_income_assessment
from app.data_foundation.seeding import seed_reference_data
from app.domain.enums import EngineAvailability, ProductType
from app.domain.production import ProductionActualInput, ProductionEngineRequest
from app.domain.units import UnitCode
from app.engines.production import production_engine, ProductionEngine
from app.models.registry import model_metadata
from app.production import repository as production_repository
from app.production.feature_adapter import LEGACY_PRODUCTION_FEATURE_ORDER, PRODUCTION_FEATURE_ADAPTER_VERSION
from app.storage.migrations import MigrationManager
from app.weather.assimilation.features import build_weather_feature_set
from app.weather.assimilation.normalizer import normalize_open_meteo_payload
from app.weather.assimilation.repository import save_run
from tests.weather_factory import RETRIEVED_AT, make_open_meteo_payload

REQUIRED_ARTIFACTS = [
    "docs/phase_4/ARCHITECTURE.md",
    "docs/phase_4/FEATURE_ADAPTER.md",
    "docs/phase_4/PRODUCTION_OUTPUT_LAYERS.md",
    "docs/phase_4/VARIETY_ADJUSTMENTS_AND_CONVERSIONS.md",
    "docs/phase_4/INTERCROP_INCOME_ASSESSMENT.md",
    "docs/phase_4/DATABASE_SCHEMA.md",
    "docs/phase_4/API.md",
    "docs/phase_4/TEST_REPORT.md",
    "docs/phase_4/USER_ACTIONS.md",
    "docs/phase_4/PHASE_4_STATUS.md",
    "docs/phase_4/RELEASE_NOTES.md",
    "manifests/phase4_feature_schema.json",
    "manifests/phase4_migration_catalog.json",
    "manifests/phase4_engine_catalog.json",
    "manifests/phase4_endpoint_catalog.json",
    "manifests/phase4_contract_hashes.json",
    "manifests/phase4_model_artifact.json",
    "manifests/phase4_intercrop_income_assessment.json",
    "manifests/phase4_source_checksums.json",
    "baseline_snapshots/phase4_test_results.txt",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 4 artifact: {relative}"
    assert settings.contract_api_version == "3.0.0-draft.10"
    assert production_engine.descriptor.availability == EngineAvailability.AVAILABLE
    assert production_engine.descriptor.version == "1.0.0"
    metadata = model_metadata("production")["production"]
    assert metadata["available"] is True
    assert metadata["version"] == "production-synthetic-1.0"
    assert metadata["features"] == LEGACY_PRODUCTION_FEATURE_ORDER
    assert PRODUCTION_FEATURE_ADAPTER_VERSION == "production-feature-adapter-1.0.0"

    raw = ROOT / "data_sources" / "raw" / "intercropping" / "Income_Assessment_RXII_2024.xlsx"
    assert raw.exists()
    assert sha256(raw) == "29a36f885cdacab4fe88b289ccf03b306a6ad2a247dadcbc63b362c45242e270"

    with tempfile.TemporaryDirectory(prefix="cocoaid-phase4-") as temp:
        database = Path(temp) / "phase4.sqlite3"
        manager = MigrationManager(database)
        assert manager.upgrade(target_version=4) == [1, 2, 3, 4]
        assert manager.upgrade(target_version=4) == []
        seeded = seed_reference_data(database_path=database)
        assert seeded["source_documents"] == 16
        assert seeded["coconut_varieties"] == 30
        assert seeded["intercrop_economic_profiles"] == 3

        normalized = normalize_open_meteo_payload(
            make_open_meteo_payload(), model="auto", forecast_days=16,
            history_days=90, retrieved_at=RETRIEVED_AT,
        )
        run_id, feature_set_id, reused = save_run(
            normalized, build_weather_feature_set(normalized), database_path=database,
        )
        assert reused is False and feature_set_id
        request = ProductionEngineRequest(
            farm_id=uuid4(), weather_feature_set_id=feature_set_id,
            farm_area_hectares=5, productive_trees=320, aging_trees=40,
            stressed_trees=20, infested_trees=5, recovering_trees=10,
            soil_ph=6.1, nitrogen_index=0.65, phosphorus_index=0.60,
            potassium_index=0.70, suitability_score=0.78, pest_probability=0.12,
            variety_id="agdt", variety_class="Unknown", intervention="none",
            baseline_annual_production_tons=25, young_nut_share=0.03,
        )
        output = ProductionEngine(database_path=database).execute(request).output
        assert str(output.feature_snapshot.weather_run_id) == run_id
        assert output.feature_snapshot.feature_order == LEGACY_PRODUCTION_FEATURE_ORDER
        assert output.forecast.raw_ml_prediction is not None and output.forecast.raw_ml_prediction >= 0
        assert output.forecast.variety_adjusted_prediction is not None and output.forecast.variety_adjusted_prediction >= 0
        assert output.forecast.posterior_status == "not_run"
        assert output.forecast.posterior_prediction is None
        assert output.forecast.variety_id == "agdt"
        assert output.forecast.variety_class.value == "Tall"
        assert output.forecast.variety_adjustment_basis
        assert output.shadow_comparison.status == "available"
        assert any(item.product == ProductType.COPRA for item in output.forecast.product_estimates)

        actual = ProductionActualInput(
            farm_id=request.farm_id, forecast_id=output.forecast.production_forecast_id,
            product=ProductType.WHOLE_NUT_WITH_HUSK,
            period_start=datetime(2026, 1, 1, tzinfo=UTC),
            period_end=datetime(2026, 12, 31, tzinfo=UTC),
            quantity=output.forecast.variety_adjusted_prediction,
            unit=UnitCode.TONNE, source_type="measured",
        )
        production_repository.save_actual(actual, database_path=database)
        performance = production_repository.forecast_performance(
            output.forecast.production_forecast_id, database_path=database,
        )
        assert performance and performance["compatible_actual_count"] == 1

        assessment = intercrop_income_assessment(database_path=database)
        assert assessment["intercrop_record_count"] == 127
        assert assessment["crop_profiles"]["cacao"]["record_count"] == 59
        assert assessment["crop_profiles"]["coffee"]["record_count"] == 68
        assert len(assessment["site_profiles"]) == 3
        assert assessment["privacy"]["farmer_names_exposed"] is False
        assert assessment["privacy"]["row_level_records_exposed"] is False

        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    result = (ROOT / "baseline_snapshots" / "phase4_test_results.txt").read_text(encoding="utf-8")
    assert "185 passed" in result
    assert "warning" not in result.lower()
    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": [1, 2, 3, 4],
        "production_engine": production_engine.descriptor.engine_id,
        "feature_adapter_version": PRODUCTION_FEATURE_ADAPTER_VERSION,
        "feature_count": len(LEGACY_PRODUCTION_FEATURE_ORDER),
        "intercrop_records_assessed": 127,
    }, indent=2))
    print("PHASE 4 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
