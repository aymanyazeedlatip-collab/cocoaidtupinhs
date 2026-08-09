from __future__ import annotations

from datetime import date
from pathlib import Path

from app.math.pest_specific import evaluate_specific_pests
from app.schemas.analysis import FarmSiteForecastRequest, PestSpecificRequest
from app.simulation.farm_site_forecast import generate_farm_site_forecast

ROOT = Path(__file__).resolve().parents[2]


def test_daily_visual_frames_cover_every_calendar_date_and_link_to_weekly_controls():
    result = generate_farm_site_forecast(FarmSiteForecastRequest(
        start_year=2026,
        end_year=2027,
        start_date=date(2026, 7, 19),
        runs=100,
        include_live_short_term=False,
    ))
    frames = result["daily_frames"]
    expected = (date(2027, 12, 31) - date(2026, 7, 19)).days + 1
    assert len(frames) == expected
    assert frames[0]["date"] == "2026-07-19"
    assert frames[-1]["date"] == "2027-12-31"
    assert result["daily_frame_count"] == expected
    assert result["playback_scale"] == "1 second equals 2 daily frames (two days)"
    assert all(0 <= int(frame["week_index"]) < len(result["weekly"]) for frame in frames)


def test_product_series_have_distinct_weather_responses_and_conserve_husk_total():
    result = generate_farm_site_forecast(FarmSiteForecastRequest(
        start_year=2026,
        end_year=2030,
        start_date=date(2026, 7, 19),
        runs=100,
        include_live_short_term=False,
    ))
    weeks = result["weekly"]
    mature = [float(row["production_coconut_mature_tons"]) for row in weeks]
    young = [float(row["production_coconut_young_tons"]) for row in weeks]
    husk = [float(row["production_coconut_w_husk_tons"]) for row in weeks]
    assert all(abs(m + y - h) < 2e-5 for m, y, h in zip(mature, young, husk))
    assert mature != young
    # Their normalized trajectories must not be identical, proving that the
    # chart's separate slopes are backed by separate weather-response factors.
    m0 = next(value for value in mature if value > 0)
    y0 = next(value for value in young if value > 0)
    mature_index = [round(value / m0, 7) for value in mature]
    young_index = [round(value / y0, 7) for value in young]
    assert mature_index != young_index
    assert any(
        row["product_response_factors"]["mature_weather_factor"]
        != row["product_response_factors"]["young_weather_factor"]
        for row in weeks
    )


def test_pest_cards_use_real_photos_with_credits_and_offline_fallbacks():
    result = evaluate_specific_pests(PestSpecificRequest())
    assert len(result["pests"]) >= 8
    for pest in result["pests"]:
        if pest["image_url"].startswith("/static/"):
            assert "-photo." in pest["image_url"]
            assert (ROOT / "app" / "static" / pest["image_url"].removeprefix("/static/")).exists()
        else:
            assert pest["image_url"].startswith("https://")
        assert pest["image_credit"]
        assert pest["image_source_url"].startswith("https://")
        assert pest["image_license"]
        assert pest["fallback_image_url"].endswith(".svg")


def test_frontend_contract_has_daily_playback_split_charts_floating_weather_and_flip_cards():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    assert 'id="weather-gis"' not in html
    assert 'id="weatherHomeMount"' in html
    assert 'id="weatherModal"' in html
    assert 'id="weatherFloatButton"' in html
    assert 'id="humidityChart"' in html
    assert 'id="cloudChart"' in html
    assert 'id="windChart"' in html
    assert 'id="pressureChart"' in html
    assert "const intervalMs = 500" in js
    assert "state.visualFrames" in js
    assert 'class="pest-card-inner"' in js
    assert 'classList.toggle("flipped")' in js
    assert "rotateY(180deg)" in css
    pdf_source = (ROOT / "app" / "reports" / "pdf.py").read_text(encoding="utf-8")
    assert '"11. Model Versions' not in pdf_source
    assert '"10. Intervention Comparison' in pdf_source


def test_weather_viewer_interpolates_every_forecast_layer_and_has_visible_wind_canvas():
    js = (ROOT / "app" / "static" / "weather-viewer" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "app" / "static" / "weather-viewer" / "styles.css").read_text(encoding="utf-8")
    assert "function renderInterpolatedForecastFrame()" in js
    assert "el.timelineSlider.step = 1" in js
    assert 'kind = "Hourly deterministic forecast"' in js
    assert "state.gridDebounce = setTimeout(loadForecastCube" in js
    assert "mix-blend-mode: screen" in css
    assert "z-index: 590" in css
