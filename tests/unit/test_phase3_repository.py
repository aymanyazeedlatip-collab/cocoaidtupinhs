from __future__ import annotations

from app.weather.assimilation.features import build_weather_feature_set
from app.weather.assimilation.normalizer import normalize_open_meteo_payload
from app.weather.assimilation.repository import (
    compare_runs,
    get_feature_set_for_run,
    get_run,
    list_runs,
    save_run,
    summary,
)
from tests.weather_factory import RETRIEVED_AT, make_open_meteo_payload


def _normalized(adjustment: float = 0.0):
    return normalize_open_meteo_payload(
        make_open_meteo_payload(forecast_rain_adjustment=adjustment),
        model="auto", forecast_days=16, history_days=90, retrieved_at=RETRIEVED_AT,
    )


def test_repository_saves_values_features_and_deduplicates_identical_run():
    run = _normalized()
    feature_set = build_weather_feature_set(run)
    run_id, feature_set_id, reused = save_run(run, feature_set)

    assert reused is False
    assert feature_set_id
    stored = get_run(run_id, include_values=True)
    assert stored is not None
    assert stored["requested_forecast_days"] == 16
    assert stored["requested_history_days"] == 90
    assert stored["values"]
    assert {item["period_kind"] for item in stored["values"]} == {"historical", "current", "forecast"}
    stored_features = get_feature_set_for_run(run_id)
    assert stored_features is not None
    assert len(stored_features["features"]) == 14

    duplicate_run_id, duplicate_feature_id, duplicate = save_run(run, build_weather_feature_set(run))
    assert duplicate is True
    assert duplicate_run_id == run_id
    assert duplicate_feature_id == feature_set_id
    counts = summary()["counts"]
    assert counts["weather_model_runs"] == 1
    assert counts["weather_feature_sets"] == 1


def test_repository_lists_filters_and_compares_versioned_runs():
    base = _normalized()
    comparison = _normalized(1.0)
    base_id, _, _ = save_run(base, build_weather_feature_set(base))
    comparison_id, _, _ = save_run(comparison, build_weather_feature_set(comparison))

    assert len(list_runs()) == 2
    assert len(list_runs(latitude=6.334, longitude=124.952)) == 2
    result = compare_runs(base_id, comparison_id)
    rain = result["metrics"]["precipitation_sum"]
    assert rain["shared_points"] == 16
    assert rain["mean_change"] == 1.0
    assert rain["maximum_absolute_change"] == 1.0
    assert result["shared_value_count"] >= 16


def test_repository_rejects_comparison_between_different_locations():
    base = _normalized()
    other_payload = make_open_meteo_payload(forecast_rain_adjustment=1.0)
    other_payload["latitude"] = 7.0
    other = normalize_open_meteo_payload(
        other_payload, model="auto", forecast_days=16, history_days=90, retrieved_at=RETRIEVED_AT,
    )
    base_id, _, _ = save_run(base, build_weather_feature_set(base))
    other_id, _, _ = save_run(other, build_weather_feature_set(other))
    try:
        compare_runs(base_id, other_id)
    except ValueError as exc:
        assert "same location" in str(exc)
    else:
        raise AssertionError("Different locations must not be compared")
