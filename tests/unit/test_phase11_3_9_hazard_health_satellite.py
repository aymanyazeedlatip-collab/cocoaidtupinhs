from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
STATUS = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")

def test_satellite_uses_visible_satellite_tile_pane():
    assert "forecastSatellitePane" in JS
    assert "forecastSatellitePane" in JS
    assert "World_Imagery/MapServer/tile" in JS
    assert "GoogleMapsCompatible_Level9" in JS
    assert 'pane.style.zIndex = "235"' in JS
    assert 'base?.setOpacity?.(0.12)' in JS
    assert 'base?.setOpacity?.(1)' in JS

def test_selected_threat_uses_compact_event_signature_without_broadcast_map():
    assert 'id="hazardEventIcon"' in HTML
    assert 'id="hazardEventBrief"' in HTML
    assert 'id="hazardWeatherRain"' in HTML
    assert 'id="hazardFocusMap"' not in HTML
    assert 'hazard-news-lower-third' not in HTML
    assert '.hazard-event-summary-visual' in CSS

def test_hazard_calendar_reserves_separate_date_and_ping_lanes():
    assert ".hazard-calendar-day > span" in CSS
    assert ".hazard-calendar-day > em" in CSS
    assert "bottom:7px" in CSS
    assert "min-height:54px" in CSS

def test_hazard_comparison_is_orange_and_red():
    assert 'backgroundColor: "rgba(255,122,40,.74)"' in JS
    assert 'backgroundColor: "rgba(191,58,47,.72)"' in JS
    assert 'borderColor: "#b83f35"' in JS

def test_health_map_centers_exactly_on_farm_bounds():
    assert "fitBounds(farmBounds" in JS
    assert "padding:[34,34]" in JS
    assert "data.polygon?.length" in JS
    assert "invalidateSize({ pan:false })" in JS

def test_health_indicators_refresh_for_selected_weather_event():
    assert "refreshHealthIndicatorsForPlan" in JS
    assert "nearestForecastFrameForDate(plan.event_start_date)" in JS
    assert "state.health.eventFrame=frame" in JS
    assert "drought_exposure:isDry?Math.max(.35,.45+.5*severity)" in JS

def test_rehabilitation_schedule_is_interactive_calendar():
    assert "renderRehabCalendar" in JS
    assert "rehabPhaseRecords" in JS
    assert "REHABILITATION CALENDAR" in JS
    assert "30-day follow-up" in JS
    assert "90-day review" in JS

def test_release_version_is_1311():
    assert "phase11-agritech-interface-1.3.23" in STATUS
    for asset in ("styles.css","phase11.css","app.js","phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML
