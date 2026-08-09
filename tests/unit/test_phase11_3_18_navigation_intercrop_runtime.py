from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
STATUS = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")
SOUP = BeautifulSoup(HTML, "html.parser")


def test_release_version_and_cache_busters_match():
    assert "phase11-agritech-interface-1.3.23" in STATUS
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML


def test_navigation_uses_requested_tabs_and_subtabs():
    direct = [node.get_text(" ", strip=True) for node in SOUP.select(".nav-direct-item .nav-label")]
    assert direct == ["Home", "Farm Profile", "About"]
    labels = [node.get_text(" ", strip=True) for node in SOUP.select(".nav-group-toggle .nav-label")]
    assert labels == ["Production Forecast", "Farm Intelligence", "Farm Operations Planning"]
    groups = {g["data-nav-group"]: [x.get("data-section") for x in g.select(".nav-subitem[data-section]")] for g in SOUP.select(".nav-group")}
    assert groups["production-forecast"] == ["outlook", "extreme-weather", "intercropping"]
    assert groups["farm-intelligence"] == ["health", "pest-risk"]
    assert groups["operations-planning"] == ["intelligence", "database", "reports"]
    assert "toggleNavGroup" in JS and "updateNavigationState" in JS
    assert ".nav-sublist.open" in CSS


def test_weather_gis_is_not_sidebar_tab_and_no_duplicate_right_button():
    assert SOUP.select_one("#nav [data-section='weather-gis-page']") is None
    assert SOUP.select_one("#weatherFloatingButton") is None
    assert SOUP.select_one("#weather-gis-page") is not None


def test_intercrop_scene_is_throttled_and_allows_deeper_zoom():
    assert ">=55" in JS
    assert "Math.min(1.05,window.devicePixelRatio||1)" in JS
    assert "Math.min(3.6" in JS
    assert "Math.max(.26" in JS
    assert "pitch-dy*.006" in JS


def test_intercrop_grid_is_transparent_and_trunks_have_variation():
    assert "rgba(248,251,252,.10)" in JS
    assert "variant:(row+Math.round((px-minX)*10))%5" in JS
    assert "trunkFill=['#8f6040'" in JS
    assert "for(let ring=0.38; ring<trunkH; ring+=0.44)" in JS


def test_auto_workflow_bootstrap_kicks_phase9_10_immediately():
    assert "/api/v2/workflows/auto-phase9-10/bootstrap" in JS
    assert "/api/v2/workflows/auto-phase9-10/kick" in JS
    assert "[800, 2200, 5200, 9000]" in JS
