from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.production import ProductionActualInput
from app.domain.enums import ProductType
from app.domain.units import UnitCode
from app.engines.production import ProductionEngine
from app.production import repository
from tests.phase4_factory import prepare_phase4_foundation, prepare_phase4_weather, production_request


def test_actual_vs_predicted_monitoring_requires_exact_product_and_unit():
    prepare_phase4_foundation()
    _, feature_set_id = prepare_phase4_weather()
    output = ProductionEngine().execute(production_request(feature_set_id)).output
    forecast = output.forecast
    actual = ProductionActualInput(
        farm_id=forecast.farm_id,
        forecast_id=forecast.production_forecast_id,
        product=ProductType.WHOLE_NUT_WITH_HUSK,
        period_start=datetime(2026, 1, 1, tzinfo=UTC),
        period_end=datetime(2026, 12, 31, tzinfo=UTC),
        quantity=forecast.variety_adjusted_prediction + 1.0,
        unit=UnitCode.TONNE,
        source_type="measured",
    )
    repository.save_actual(actual)
    repository.save_actual(actual.model_copy(update={"product": ProductType.COPRA, "unit": UnitCode.KILOGRAM}))
    with pytest.raises(ValueError, match="farm_id does not match"):
        repository.save_actual(actual.model_copy(update={"farm_id": uuid4()}))
    performance = repository.forecast_performance(forecast.production_forecast_id)
    assert performance["compatible_actual_count"] == 1
    assert performance["comparisons"][0]["error"] == 1.0
    assert repository.get_forecast(forecast.production_forecast_id)["posterior_status"] == "not_run"
