from datetime import date
from pathlib import Path

from app.schemas.analysis import FarmSiteForecastRequest
from app.simulation.farm_site_forecast import generate_farm_site_forecast

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
STATUS = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")

def test_hazard_broadcast_map_removed_and_summary_cards_have_visual_gauges():
    assert 'id="hazardFocusMap"' not in HTML
    assert 'id="hazardEventBrief"' in HTML
    for gauge in ("hazardCountGauge", "hazardPeakGauge", "hazardLossGauge", "hazardTreesGauge"):
        assert f'id="{gauge}"' in HTML
    assert "setHazardGauge" in JS

def test_hazard_event_list_removes_legacy_ping_and_uses_readable_spacing():
    assert ".hazard-list .hazard-item::before" in CSS
    assert "display:none !important" in CSS
    assert "grid-template-columns:116px minmax(0,1fr)" in CSS
    assert "font-size:13px !important" in CSS

def test_hazard_weather_values_are_period_aggregated():
    assert "hazardEventWeatherSummary" in JS
    assert "event_rainfall_total_mm" in JS
    assert "event_peak_temperature_c" in JS
    result = generate_farm_site_forecast(FarmSiteForecastRequest(
        start_year=2026, end_year=2032, start_date=date(2026, 1, 1), runs=100, include_live_short_term=False
    ))
    rain_events = [e for e in result["extreme_events"] if e["event_type"] == "extreme_rain"]
    heat_events = [e for e in result["extreme_events"] if e["event_type"] == "heat_stress"]
    assert rain_events
    assert heat_events
    assert all(e["event_rainfall_total_mm"] >= 70 for e in rain_events)
    assert all(e["event_peak_temperature_c"] >= 33 for e in heat_events)

def test_farm_health_calendar_is_in_side_rail_and_map_is_dominant():
    side_start = HTML.index('<div class="health-map-side">')
    schedule = HTML.index('id="rehabSchedule"')
    assert schedule > side_start
    assert "grid-template-columns:minmax(0,2.15fr) minmax(330px,.72fr)" in CSS
    assert "height:clamp(610px,72vh,840px)" in CSS

def test_pest_risk_has_enhanced_visual_hierarchy_and_spacing():
    assert 'class="pest-intro-chips"' in HTML
    assert "grid-template-columns:repeat(3,minmax(280px,1fr))" in CSS
    assert ".pest-card-title strong" in CSS
    assert "font-size:15px !important" in CSS
    assert ".pest-card-back ul" in CSS
    assert "line-height:1.58 !important" in CSS

def test_release_version_is_1311():
    assert "phase11-agritech-interface-1.3.23" in STATUS
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML
