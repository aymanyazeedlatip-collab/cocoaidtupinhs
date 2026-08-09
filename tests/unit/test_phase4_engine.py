from __future__ import annotations

from app.domain.enums import EngineAvailability, ProductType
from app.engines.production import ProductionEngine
from app.engines.registry import engine_registry
from app.production import repository
from tests.phase4_factory import prepare_phase4_foundation, prepare_phase4_weather, production_request


def test_phase4_production_engine_registered_and_executes_retained_model():
    prepare_phase4_foundation()
    _, feature_set_id = prepare_phase4_weather()
    descriptor = engine_registry.descriptor("v3.production")
    assert descriptor.availability == EngineAvailability.AVAILABLE
    engine = ProductionEngine()
    result = engine.execute(production_request(feature_set_id))
    output = result.output
    assert result.engine_id == "v3.production"
    assert output.forecast.raw_ml_prediction >= 0
    assert output.forecast.variety_adjusted_prediction >= 0
    assert output.forecast.posterior_status == "not_run"
    assert output.forecast.posterior_prediction is None
    assert output.forecast.variety_id == "agdt"
    assert output.forecast.variety_class.value == "Tall"
    assert "Within-tall adjustment" in output.forecast.variety_adjustment_basis
    assert output.forecast.variety_adjustment_basis not in output.warnings
    assert output.feature_snapshot.features["variety"] == "Tall"
    assert output.shadow_comparison.status == "available"
    assert any(item.product == ProductType.COPRA for item in output.forecast.product_estimates)
    assert repository.summary()["production_forecasts_v3"] == 1


def test_phase4_production_engine_is_numerically_deterministic_for_same_inputs():
    prepare_phase4_foundation()
    _, feature_set_id = prepare_phase4_weather()
    request = production_request(feature_set_id)
    engine = ProductionEngine()
    first = engine.execute(request).output
    second = engine.execute(request).output
    assert first.forecast.raw_ml_prediction == second.forecast.raw_ml_prediction
    assert first.forecast.variety_adjusted_prediction == second.forecast.variety_adjusted_prediction
    assert first.feature_snapshot.feature_sha256 == second.feature_snapshot.feature_sha256


def test_phase4_unknown_named_variety_uses_supplied_legacy_class_without_adjustment():
    prepare_phase4_foundation()
    _, feature_set_id = prepare_phase4_weather()
    result = ProductionEngine().execute(production_request(
        feature_set_id, variety_id="not-real", variety_class="Hybrid", baseline_annual_production_tons=None,
    )).output
    assert result.forecast.variety_id is None
    assert result.forecast.variety_class.value == "Hybrid"
    assert result.forecast.variety_adjustment_factor == 1.0
    assert result.shadow_comparison.status == "not_available"
    assert any("was not found" in warning for warning in result.warnings)
