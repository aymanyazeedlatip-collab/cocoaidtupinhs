from __future__ import annotations

from app.domain.enums import ProductType
from app.domain.production import LegacyVarietyClass
from app.production.conversions import (
    MAX_VARIETY_FACTOR,
    MIN_VARIETY_FACTOR,
    build_product_estimates,
    load_variety_parameters,
    variety_adjustment_factor,
)
from tests.phase4_factory import prepare_phase4_foundation


def test_named_variety_factor_is_bounded_and_uses_class_reference():
    prepare_phase4_foundation()
    variety, params, warnings = load_variety_parameters("agdt", LegacyVarietyClass.UNKNOWN)
    assert variety and variety["variety_class"] == "tall"
    assert "nuts_per_hectare" in params
    factor, basis, factor_warnings = variety_adjustment_factor(variety, params, LegacyVarietyClass.TALL)
    assert MIN_VARIETY_FACTOR <= factor <= MAX_VARIETY_FACTOR
    assert "Within-tall adjustment" in basis
    assert warnings == []
    assert isinstance(factor_warnings, list)


def test_product_conversions_keep_direct_output_and_use_mature_nut_components():
    prepare_phase4_foundation()
    _, params, _ = load_variety_parameters("agdt", LegacyVarietyClass.TALL)
    estimates, warnings = build_product_estimates(10.0, params, young_nut_share=0.10)
    by_product = {item.product: item for item in estimates}
    assert by_product[ProductType.WHOLE_NUT_WITH_HUSK].quantity == 10.0
    assert by_product[ProductType.MATURE_NUT].quantity > by_product[ProductType.YOUNG_NUT].quantity
    assert by_product[ProductType.COPRA].quantity > 0
    assert "mature-nut count" in by_product[ProductType.COPRA].conversion_basis
    assert not any("fruit weight is unavailable" in item for item in warnings)


def test_missing_named_variety_parameters_do_not_invent_conversions():
    estimates, warnings = build_product_estimates(8.0, {}, young_nut_share=0.03)
    assert len(estimates) == 1
    assert estimates[0].product == ProductType.WHOLE_NUT_WITH_HUSK
    assert any("fruit weight is unavailable" in item for item in warnings)
