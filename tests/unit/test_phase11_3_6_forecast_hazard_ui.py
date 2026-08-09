from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
APP = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
SOUP = BeautifulSoup(HTML, "html.parser")


def test_weather_gis_is_removed_from_primary_navigation_without_duplicate_right_button():
    items = SOUP.select("#nav [data-section]")
    assert "weather-gis-page" not in [item["data-section"] for item in items]
    assert SOUP.select_one("#weatherFloatingButton") is None
    assert SOUP.select_one("#weather-gis-page") is not None


def test_productivity_has_no_duplicate_weather_gis_embed():
    assert SOUP.select_one("#forecastWeatherViewerFrame") is None
    assert "forecast-weather-frame-shell" not in HTML
    assert "16-Day Weather GIS &amp; Layer Controls" not in HTML


def test_long_term_forecast_is_fullscreen_map_with_collapsible_floating_ui():
    assert SOUP.select_one("#outlook.forecast-fullscreen-page") is not None
    assert SOUP.select_one("#forecastMapWorkspace") is not None
    assert SOUP.select_one("#forecastMap.forecast-map-fullscreen") is not None
    for panel in ("summary", "layers", "graphs", "timeline"):
        assert SOUP.select_one(f'[data-forecast-panel="{panel}"]') is not None
        assert SOUP.select_one(f'[data-forecast-panel-body="{panel}"]') is not None
    assert "#outlook.forecast-fullscreen-page" in CSS
    assert "width: 100vw !important" in CSS
    assert "height: 100dvh !important" in CSS
    assert "function setForecastPanel(name, forceOpen = null)" in APP


def test_first_16_days_use_hourly_provider_frames_then_daily():
    assert "forecast_hours: 384" in APP
    assert "function buildHourlyProviderFrames" in APP
    assert 'visual_resolution: "hourly_provider"' in APP
    assert 'frame.data_mode !== "deterministic_short_term_forecast"' in APP
    assert "Hourly forecast steps" in HTML
    assert "DAY 17 → 2050 · DAILY" in HTML
    assert "Daily modeled snapshots" in HTML


def test_forecast_wind_matches_weather_gis_particle_style_and_uses_grid_terrain():
    assert SOUP.select_one("#forecastWindCanvas") is not None
    for token in (
        "resizeForecastWindCanvas",
        "animateForecastWind",
        "drawForecastWindArrow",
        "forecastVectorMatrixAt",
        "forecastApplyTerrainDeflection",
        "requestAnimationFrame(animateForecastWind)",
    ):
        assert token in APP
    assert 'ctx.strokeStyle = "rgba(247,255,250,.96)"' in APP
    assert ".forecast-wind-canvas" in CSS and "pointer-events:none" in CSS


def test_satellite_filter_uses_same_nasa_gibs_source_as_weather_gis():
    assert SOUP.select_one('[data-forecast-map-layer="satellite"]') is not None
    assert "MODIS_Terra_CorrectedReflectance_TrueColor" in APP
    assert "gibs.earthdata.nasa.gov" in APP
    assert "Satellite imagery NASA EOSDIS GIBS" in APP


def test_extreme_weather_redesign_keeps_full_detail_but_prioritizes_selected_threat():
    for element_id in (
        "hazardCount", "hazardPeak", "hazardLoss", "hazardTrees",
        "hazardFocusType", "hazardFocusWindow", "hazardFocusSeverity",
        "hazardFocusLoss", "hazardFocusTrees", "hazardFocusConfidence",
        "hazardFocusSource", "hazardTimeline", "hazardDateRail", "hazardChart",
    ):
        assert SOUP.find(id=element_id) is not None
    assert SOUP.select_one("details.hazard-technical-panel") is not None
    assert "SELECTED THREAT" in HTML
    assert "All flagged periods" in HTML
    assert "Technical comparison" in HTML
    assert 'selectedEvent.data_mode === "deterministic_short_term_forecast"' in APP
    assert "hazardFocusSeverityBar" in APP
    assert "hazardFocusLossBar" in APP


def test_no_duplicate_dom_ids_after_forecast_and_hazard_rework():
    ids = [tag["id"] for tag in SOUP.find_all(id=True)]
    assert len(ids) == len(set(ids))
