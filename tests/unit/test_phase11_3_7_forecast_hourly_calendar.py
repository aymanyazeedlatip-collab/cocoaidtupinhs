from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
APP = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
WEATHER = (ROOT / "app/static/weather-viewer/app.js").read_text(encoding="utf-8")
SOUP = BeautifulSoup(HTML, "html.parser")


def test_provider_forecast_uses_original_hourly_cube_frames():
    assert "function buildHourlyProviderFrames" in APP
    assert 'visual_resolution: "hourly_provider"' in APP
    assert "position += .25" not in APP
    assert "forecast_hours: 384" in APP
    assert "DAY 1–16 · HOURLY" in HTML
    assert "Hourly forecast steps" in HTML


def test_weather_gis_forecast_playback_is_hourly_too():
    assert "el.timelineSlider.step = 1;" in WEATHER
    assert "let next = Number(el.timelineSlider.value) + 1;" in WEATHER
    assert 'kind = "Hourly deterministic forecast";' in WEATHER
    assert "quarter-hour visual interpolation" not in WEATHER


def test_interactive_calendar_coexists_with_persistent_range_timeline():
    for element_id in (
        "forecastCalendar", "forecastCalendarPrev", "forecastCalendarNext",
        "forecastCalendarMonth", "forecastCalendarGrid", "forecastHourPicker",
        "forecastHourScroll", "forecastHourLabel",
    ):
        assert SOUP.find(id=element_id) is not None
    assert SOUP.select_one("#forecastSlider.forecast-slider-visible") is not None
    assert "forecast-timeline-dock .timeline-strip { display:none !important" in CSS
    assert ".forecast-timeline-dock.calendar-open .timeline-strip { display:block !important" in CSS
    assert "function renderForecastCalendar" in APP
    assert "function shiftForecastCalendarMonth" in APP
    assert "data-forecast-date" in APP
    assert "data-forecast-index" in APP


def test_forecast_panels_are_closed_by_default_and_mutually_exclusive():
    assert "open" not in (SOUP.select_one("#forecastSummaryPanel").get("class") or [])
    assert "calendar-open" not in (SOUP.select_one("#forecastTimelineDock").get("class") or [])
    assert 'timeline.classList.toggle("calendar-open", shouldOpen)' in APP
    assert 'timeline?.classList.remove("calendar-open")' in APP


def test_forecast_map_is_true_full_bleed_and_shortcuts_do_not_cover_it():
    assert 'body[data-active-section="outlook"] .app-shell' in CSS
    assert '#forecastMap.leaflet-container' in CSS
    assert 'height:100dvh !important' in CSS
    assert 'body[data-active-section="outlook"] .weather-float' in CSS
    assert 'body[data-active-section="outlook"] .pilot-float' in CSS


def test_liquid_glass_and_legible_forecast_controls_are_applied():
    assert "backdrop-filter:blur(22px) saturate(1.18)" in CSS
    assert ".forecast-tool-button" in CSS
    assert "font-size:25px !important" in CSS
    assert ".forecast-calendar-day" in CSS


def test_forecast_wind_uses_weather_gis_animation_parameters():
    for token in (
        "Math.max(95", "Math.min(340", "/ 4200",
        "rgba(247,255,250,.96)", "ctx.shadowBlur = 2.2", "ctx.lineWidth = 1.35",
        "Math.max(7, Math.min(18", "magnitude * .055",
    ):
        assert token in APP
    for token in (
        "const count = Math.max(", "Math.min(340", "/ 4200",
        "rgba(247,255,250,.96)", "ctx.shadowBlur = 2.2", "ctx.lineWidth = 1.35",
        "Math.max(7, Math.min(18", "magnitude * 0.055",
    ):
        assert token in WEATHER
    assert "forecastVectorMatrixAt" in APP
    assert "forecastApplyTerrainDeflection" in APP
    assert "display:block !important" in CSS
    assert "mix-blend-mode:screen !important" in CSS


def test_asset_cache_version_and_interface_version_are_current():
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML
    status = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")
    assert 'phase11-agritech-interface-1.3.23' in status
