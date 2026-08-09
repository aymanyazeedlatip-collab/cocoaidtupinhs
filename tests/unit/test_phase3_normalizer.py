from __future__ import annotations

from datetime import timedelta

from app.domain.enums import DataQualityFlag
from app.weather.assimilation.normalizer import live_only_payload, normalize_open_meteo_payload
from tests.weather_factory import RETRIEVED_AT, make_open_meteo_payload


def test_live_payload_contains_current_and_no_more_than_sixteen_days():
    payload = make_open_meteo_payload()
    live = live_only_payload(payload, forecast_days=16, retrieved_at=RETRIEVED_AT)

    assert live["historical_values_included"] is False
    assert live["forecast_horizon_days"] == 16
    assert len(live["daily"]["time"]) == 16
    assert live["daily"]["time"][0] == "2026-08-03"
    assert live["daily"]["time"][-1] == "2026-08-18"
    assert live["hourly"]["time"][0].startswith("2026-08-03T14")
    assert all(item >= "2026-08-03" for item in live["daily"]["time"])


def test_normalizer_separates_history_current_and_forecast_and_is_deterministic():
    payload = make_open_meteo_payload()
    first = normalize_open_meteo_payload(
        payload, model="auto", forecast_days=16, history_days=90, retrieved_at=RETRIEVED_AT,
    )
    second = normalize_open_meteo_payload(
        payload, model="auto", forecast_days=16, history_days=90, retrieved_at=RETRIEVED_AT,
    )

    assert first.raw_payload_sha256 == second.raw_payload_sha256
    assert first.valid_to - first.valid_from <= timedelta(days=16)
    assert {item.period_kind for item in first.values} == {"historical", "current", "forecast"}
    historical = [item for item in first.values if item.period_kind == "historical"]
    assert historical
    assert all(DataQualityFlag.REFERENCE_ONLY.value in item.quality_flags for item in historical)
    assert DataQualityFlag.REFERENCE_ONLY.value in first.quality_flags
    assert first.provider_metadata["provider_run_time_exposed"] is False
    assert first.provider_run_at is None
    assert first.is_stale is False
    assert "metadata" not in first.payload_for_storage


def test_normalizer_marks_stale_cached_provider_data():
    normalized = normalize_open_meteo_payload(
        make_open_meteo_payload(stale=True), model="auto", forecast_days=16,
        history_days=0, retrieved_at=RETRIEVED_AT,
    )
    assert normalized.is_stale is True
    assert DataQualityFlag.STALE.value in normalized.quality_flags


def test_normalizer_rejects_missing_hourly_series():
    payload = make_open_meteo_payload()
    payload.pop("hourly")
    try:
        normalize_open_meteo_payload(payload, model="auto", forecast_days=16, history_days=90)
    except ValueError as exc:
        assert "hourly" in str(exc)
    else:
        raise AssertionError("Missing hourly data should fail explicitly")


def test_weather_model_run_contract_allows_unknown_provider_initialization_time():
    from app.domain.enums import SourceType, WeatherDataKind
    from app.domain.provenance import SourceReference
    from app.domain.units import UnitCode
    from app.domain.weather import WeatherModelRun, WeatherVariable

    run = WeatherModelRun(
        provider="Open-Meteo",
        provider_model="auto",
        data_kind=WeatherDataKind.FORECAST,
        model_run_at=None,
        retrieved_at=RETRIEVED_AT,
        valid_from=RETRIEVED_AT,
        valid_to=RETRIEVED_AT + timedelta(days=16),
        latitude=6.334,
        longitude=124.952,
        variables=[WeatherVariable.PRECIPITATION],
        units={WeatherVariable.PRECIPITATION: UnitCode.MILLIMETER},
        source=SourceReference(
            source_id="open-meteo", title="Open-Meteo forecast", source_type=SourceType.WEATHER_PROVIDER,
        ),
        provider_metadata={"provider_run_time_exposed": False},
    )
    assert run.model_run_at is None
