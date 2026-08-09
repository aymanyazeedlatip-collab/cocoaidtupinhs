from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.schemas.analysis import FarmSiteForecastRequest
from app.schemas.farm import FarmCreate
from app.simulation.farm_site_forecast import _aggregate_live_cube, generate_farm_site_forecast


def fake_cube(start: datetime | None = None, hours: int = 72) -> dict:
    start = start or datetime(2026, 7, 19, tzinfo=timezone.utc)
    times = [(start + timedelta(hours=i)).isoformat() for i in range(hours)]
    points = 36
    cube = {
        "rows": 6,
        "cols": 6,
        "west": 123.5,
        "east": 126.5,
        "south": 5.0,
        "north": 8.0,
        "latitudes": [8.0, 7.4, 6.8, 6.2, 5.6, 5.0],
        "longitudes": [123.5, 124.1, 124.7, 125.3, 125.9, 126.5],
        "times": times,
        "values": {},
        "metadata": {"source": "Mock numerical model", "source_type": "Deterministic forecast", "is_stale": False},
    }
    patterns = {
        "precipitation": lambda point, hour: 6.0 if point == 16 and 24 <= hour < 28 else (0.4 if hour % 7 == 0 else 0.0),
        "temperature_2m": lambda point, hour: 27.0 + (hour % 24) / 24,
        "cloud_cover": lambda point, hour: 82.0,
        "pressure_msl": lambda point, hour: 1008.0,
        "wind_speed_10m": lambda point, hour: 14.0,
        "wind_direction_10m": lambda point, hour: 90.0,
        "relative_humidity_2m": lambda point, hour: 84.0,
    }
    for variable, fn in patterns.items():
        cube["values"][variable] = [[fn(point, hour) for hour in range(hours)] for point in range(points)]
    return cube


def test_live_cube_is_aggregated_to_manila_days_and_retains_spatial_grid():
    daily, metadata = _aggregate_live_cube(fake_cube(hours=48), FarmCreate())
    assert daily
    assert metadata["timezone"] == "Asia/Manila"
    first = daily[min(daily)]
    assert first["data_mode"] == "deterministic_short_term_forecast"
    assert len(first["spatial_grid"]) == 6
    assert len(first["spatial_grid"][0]) == 6
    assert 0 <= first["humidity_percent"] <= 100


def test_farm_site_forecast_starts_on_selected_date_and_switches_data_modes():
    request = FarmSiteForecastRequest(
        start_year=2026,
        end_year=2027,
        start_date=date(2026, 7, 19),
        runs=100,
        include_live_short_term=True,
    )
    result = generate_farm_site_forecast(request, fake_cube(hours=72))
    assert result["frames"][0]["date"] == "2026-07-19"
    assert result["frames"][0]["data_mode"] == "deterministic_short_term_forecast"
    assert any(frame["data_mode"] == "plausible_stochastic_climate_simulation" for frame in result["frames"])
    assert result["short_term_live_merge"]["available"] is True
    assert result["short_term_live_merge"]["dates_merged"] >= 3
    assert result["frames"][-1]["week_end"] == "2027-12-31"


def test_weekly_three_product_equivalents_do_not_claim_exact_harvest():
    result = generate_farm_site_forecast(FarmSiteForecastRequest(
        start_year=2026, end_year=2027, start_date=date(2026, 7, 19), runs=100,
        include_live_short_term=False,
    ))
    assert "equivalent" in result["production_label"].lower()
    assert all(frame["production_coconut_w_husk_tons"] >= 0 for frame in result["frames"])
    assert all(abs(frame["production_coconut_mature_tons"] + frame["production_coconut_young_tons"] - frame["production_coconut_w_husk_tons"]) < 2e-5 for frame in result["frames"])
    assert result["timeline_resolution"] == "daily_visual_frames_with_weekly_agricultural_control_points"
    assert result["daily_frame_count"] == len(result["daily_frames"])
    assert any("not a guaranteed harvest" in warning for warning in result["warnings"])


def test_start_date_must_match_start_year():
    with pytest.raises(ValueError):
        FarmSiteForecastRequest(start_year=2026, end_year=2027, start_date=date(2027, 1, 1))


def test_full_year_three_product_totals_match_annual_state_and_partial_year_is_labeled():
    result = generate_farm_site_forecast(FarmSiteForecastRequest(
        start_year=2026, end_year=2027, start_date=date(2026, 7, 19), runs=100,
        include_live_short_term=False,
    ))
    first, second = result["annual_by_product"]
    assert first["coverage_label"].startswith("partial")
    assert 0 < first["coverage_ratio"] < 1
    assert second["coverage_label"] == "full year"
    annual_2027 = next(row for row in result["annual_states"] if row["year"] == 2027)
    assert abs(second["coconut_w_husk_tons"] - annual_2027["annual_production_tons"]) < 0.01
    assert abs(second["coconut_mature_tons"] + second["coconut_young_tons"] - second["coconut_w_husk_tons"]) < 1e-9
