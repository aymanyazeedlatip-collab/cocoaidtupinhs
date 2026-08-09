from __future__ import annotations

import math

from app.domain.enums import DataQualityFlag
from app.weather.assimilation.features import FEATURE_ADAPTER_VERSION, build_weather_feature_set
from app.weather.assimilation.normalizer import normalize_open_meteo_payload
from tests.weather_factory import RETRIEVED_AT, make_open_meteo_payload


def _feature_map(feature_set):
    return {item.name: item for item in feature_set.features}


def test_weather_features_are_numerically_correct_and_traceable():
    run = normalize_open_meteo_payload(
        make_open_meteo_payload(), model="auto", forecast_days=16, history_days=90,
        retrieved_at=RETRIEVED_AT,
    )
    feature_set = build_weather_feature_set(run)
    features = _feature_map(feature_set)

    assert feature_set.feature_adapter_version == FEATURE_ADAPTER_VERSION
    assert feature_set.latitude == 6.334
    assert feature_set.longitude == 124.952
    assert len(features) == 14
    assert features["rainfall_7d_mm"].value == 9.5
    assert features["rainfall_30d_mm"].value == 55.5
    assert features["rainfall_90d_mm"].value == 175.5
    assert features["moisture_balance_30d_mm"].value == 25.5
    assert features["moisture_balance_90d_mm"].value == 85.5
    assert features["consecutive_dry_days"].value == 3.0
    assert features["heat_stress_days_30d"].value == 6.0
    assert features["forecast_rainfall_16d_mm"].value == 30.5
    assert features["forecast_heat_stress_days_16d"].value == 4.0
    assert math.isclose(features["forecast_max_wind_gust_16d_kmh"].value, 27.5)
    assert features["mean_solar_radiation_90d_mj_m2_day"].value == 18.0
    assert features["mean_relative_humidity_30d_percent"].value == 75.0
    assert math.isclose(features["mean_vpd_30d_kpa"].value, 0.8)
    assert math.isclose(features["mean_soil_moisture_30d_fraction"].value, 0.31)

    historical_flags = features["rainfall_30d_mm"].quality_flags
    assert DataQualityFlag.REFERENCE_ONLY in historical_flags
    assert DataQualityFlag.MISSING not in historical_flags
    assert all(math.isfinite(item.value) for item in feature_set.features)


def test_feature_values_are_deterministic_for_identical_input():
    run = normalize_open_meteo_payload(
        make_open_meteo_payload(), model="auto", forecast_days=16, history_days=90,
        retrieved_at=RETRIEVED_AT,
    )
    one = build_weather_feature_set(run)
    two = build_weather_feature_set(run)
    assert [(item.name, item.value, item.unit) for item in one.features] == [
        (item.name, item.value, item.unit) for item in two.features
    ]
    assert one.feature_set_id != two.feature_set_id


def test_missing_history_is_flagged_instead_of_imputed():
    run = normalize_open_meteo_payload(
        make_open_meteo_payload(), model="auto", forecast_days=16, history_days=0,
        retrieved_at=RETRIEVED_AT,
    )
    features = _feature_map(build_weather_feature_set(run))
    assert DataQualityFlag.LOW_TEMPORAL_RESOLUTION in features["rainfall_30d_mm"].quality_flags
    assert DataQualityFlag.REFERENCE_ONLY in features["rainfall_30d_mm"].quality_flags
