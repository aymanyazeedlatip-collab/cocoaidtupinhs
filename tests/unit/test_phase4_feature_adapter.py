from __future__ import annotations

import pytest

from app.core.errors import EngineExecutionError
from app.models.registry import load_model
from app.production.feature_adapter import (
    LEGACY_PRODUCTION_FEATURE_ORDER,
    PRODUCTION_FEATURE_ADAPTER_VERSION,
    build_feature_snapshot,
    verify_artifact_feature_contract,
)
from tests.phase4_factory import prepare_phase4_foundation, prepare_phase4_weather, production_request


def test_phase4_feature_adapter_freezes_artifact_order_and_hashes_payload():
    prepare_phase4_foundation()
    run_id, feature_set_id = prepare_phase4_weather()
    snapshot = build_feature_snapshot(production_request(feature_set_id))
    assert str(snapshot.weather_run_id) == run_id
    assert snapshot.feature_adapter_version == PRODUCTION_FEATURE_ADAPTER_VERSION
    assert snapshot.feature_order == LEGACY_PRODUCTION_FEATURE_ORDER
    assert snapshot.feature_order == load_model("production")["features"]
    assert snapshot.features["variety"] == "Tall"
    assert snapshot.features["annual_rainfall_mm"] >= 0
    assert len(snapshot.feature_sha256) == 64
    verify_artifact_feature_contract()


def test_phase4_feature_adapter_is_deterministic_for_identical_inputs():
    prepare_phase4_foundation()
    _, feature_set_id = prepare_phase4_weather()
    request = production_request(feature_set_id)
    first = build_feature_snapshot(request)
    second = build_feature_snapshot(request)
    assert first.feature_sha256 == second.feature_sha256
    assert first.ordered_values == second.ordered_values


def test_phase4_feature_adapter_rejects_unknown_weather_feature_set():
    prepare_phase4_foundation()
    request = production_request("00000000-0000-0000-0000-000000000099")
    with pytest.raises(EngineExecutionError, match="Weather feature set not found"):
        build_feature_snapshot(request)
