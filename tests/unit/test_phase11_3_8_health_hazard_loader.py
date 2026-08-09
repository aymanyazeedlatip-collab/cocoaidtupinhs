from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
APP = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
SOUP = BeautifulSoup(HTML, "html.parser")


def test_forecast_slider_is_persistent_and_calendar_is_optional():
    slider = SOUP.select_one("#forecastSlider.forecast-slider-visible")
    calendar = SOUP.select_one("#forecastTimelineStrip")
    toggle = SOUP.select_one("#forecastTimelineCollapse")
    assert slider is not None and calendar is not None and toggle is not None
    assert toggle.get("aria-expanded") == "false"
    assert "forecast-timeline-dock .timeline-strip { display:none !important" in CSS
    assert ".forecast-timeline-dock.calendar-open .timeline-strip { display:block !important" in CSS
    assert 'timeline.classList.toggle("calendar-open", shouldOpen)' in APP


def test_forecast_layers_use_switch_controls():
    buttons = SOUP.select("[data-forecast-map-layer]")
    assert len(buttons) == 4
    assert {b.get("data-forecast-map-layer") for b in buttons} == {"rain", "wind", "satellite", "farm"}
    assert all(b.select_one(".forecast-layer-toggle") for b in buttons)
    assert ".forecast-layer-toggle" in CSS
    assert "translateX(20px)" in CSS
    assert ".forecast-layer-status" in CSS


def test_forecast_wind_overrides_legacy_display_none_and_matches_weather_gis_visual_style():
    assert '#forecastMap + canvas,#forecastWindCanvas { display:none !important; }' in (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert "#forecastWindCanvas.forecast-wind-canvas {" in CSS
    assert "display:block !important" in CSS
    assert "z-index:590 !important" in CSS
    assert "mix-blend-mode:screen !important" in CSS
    assert "drop-shadow(0 0 1.25px rgba(0,0,0,.55))" in CSS
    for token in ("forecastVectorMatrixAt", "forecastApplyTerrainDeflection", "forecastApplyFarmTerrainProxy", "forecastUniformWindVector"):
        assert token in APP
    for token in ('rgba(247,255,250,.96)', "ctx.shadowBlur = 2.2", "ctx.lineWidth = 1.35"):
        assert token in APP


def test_extreme_weather_uses_calendar_with_separate_date_and_dot_zones():
    assert SOUP.select_one("#hazardDateRail.hazard-calendar-shell") is not None
    assert "function renderHazardCalendar" in APP
    assert "hazard-calendar-day" in APP
    assert ".hazard-calendar-day > span" in CSS
    assert ".hazard-calendar-day > em" in CSS
    assert "bottom:6px" in CSS
    assert "hazard-calendar-legend" in HTML


def test_farm_health_is_map_first_and_pest_cards_are_not_inside_health():
    health = SOUP.select_one("#health")
    assert health is not None
    assert health.select_one("#rehabMap") is not None
    assert health.select_one("#healthOverviewChart") is not None
    assert health.select_one("#treeStateChart") is not None
    assert health.select_one("#pestCardDeck") is None
    assert "health-map-stage" in HTML
    assert ".health-primary-map #rehabMap" in CSS


def test_pest_risk_has_dedicated_navigation_and_visualizations():
    pest_nav = SOUP.select_one('.nav-item[data-section="pest-risk"]')
    pest_page = SOUP.select_one("#pest-risk")
    assert pest_nav is not None and pest_page is not None
    for chart_id in ("pestRankingChart", "pestDriverChart"):
        assert pest_page.select_one(f"#{chart_id}") is not None
    assert pest_page.select_one("#pestCardDeck") is not None
    assert "function renderPestVisuals" in APP


def test_grouped_navigation_keeps_weather_gis_outside_sidebar():
    nav = SOUP.select_one("#nav")
    sections = [button.get("data-section") for button in nav.select(".nav-item[data-section]")]
    assert "weather-gis-page" not in sections
    assert sections.index("pest-risk") > sections.index("health")
    assert SOUP.select_one("#weatherFloatingButton") is None


def test_loading_screen_has_green_glass_tree_hologram_and_segmented_progress():
    overlay = SOUP.select_one("#loadingOverlay")
    tree = SOUP.select_one(".loading-mini-hologram[data-hologram-start-offset-ms]")
    bar = SOUP.select_one("#loadingSegmentBar")
    assert overlay is not None and tree is not None and bar is not None
    assert len(bar.select("i")) == 12
    assert bar.get("role") == "progressbar"
    assert "rgba(12,73,37,.84)" in CSS
    assert ".loading-mini-hologram" in CSS
    assert ".loading-segment-bar" in CSS
    assert "function updateLoadingSegments" in APP
    assert "state.loadingProgressTimer" in APP
