from __future__ import annotations

import json
from pathlib import Path


from app.coco_pilot.reports import FORMAL_REPORT_GENERATOR_VERSION
from app.interface.status import (
    DESIGN_SYSTEM_VERSION,
    INTERFACE_VERSION,
    REPORT_PRESENTATION_VERSION,
    WEATHER_GIS_UI_VERSION,
    interface_status,
)

ROOT = Path(__file__).resolve().parents[2]


def test_phase11_interface_status_declares_required_design_policy() -> None:
    status = interface_status()
    assert status["interface_id"] == "v3.interface"
    assert status["version"] == INTERFACE_VERSION
    assert status["design_system_version"] == DESIGN_SYSTEM_VERSION
    assert status["weather_gis_ui_version"] == WEATHER_GIS_UI_VERSION
    assert status["report_presentation_version"] == REPORT_PRESENTATION_VERSION
    assert status["theme"]["default"] == "official_white"
    assert status["theme"]["liquid_glass_enabled"] is False
    assert status["theme"]["solid_surfaces"] is True
    assert status["landing"]["interactive_coconut_hologram"] is True
    assert status["audio"]["background_music_preserved"] is True
    assert status["audio"]["voice_lines_preserved"] is True
    assert status["visualizations"]["chart_csv_export"] is True
    assert status["visualizations"]["chart_fullscreen"] is True


def test_phase11_main_html_contains_hologram_weather_and_decision_pages() -> None:
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    for token in (
        'href="/static/phase11.css?v=11.3.23"', 'src="/static/phase11.js?v=11.3.23"',
        'id="globalNavButton"', 'id="coconutHologramWorkspace"',
        'id="weather-gis-page"', 'id="weatherDedicatedFrame"',
        'id="intelligence"', 'id="phase11EngineGrid"',
        'data-section="intelligence"',
    ):
        assert token in html
    assert 'id="coconutHologramPreview"' not in html
    assert 'class="farmer-home-hero"' in html


def test_phase11_css_disables_liquid_glass_and_uses_logo_palette() -> None:
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    assert "backdrop-filter: none !important" in css
    assert "--green: #246b32" in css
    assert "--green-bright: #6fae22" in css
    assert "--orange: #ef8500" in css
    assert "--brown: #724413" in css
    assert ".coconut-hologram" in css
    assert ".phase11-chart-tools" in css
    assert ".weather-dedicated-shell" in css
    assert ".phase11-intelligence-grid" in css


def test_phase11_chart_controls_and_hologram_are_interactive() -> None:
    javascript = (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
    for feature in (
        "pointerdown",
        "ArrowLeft",
        "Download PNG",
        "Export CSV",
        "Full screen",
        "getChart",
        "phase11RefreshIntelligence",
    ):
        assert feature in javascript


def test_phase11_weather_viewer_uses_official_solid_interface() -> None:
    html = (ROOT / "app/static/weather-viewer/index.html").read_text(encoding="utf-8")
    assert 'href="/static/weather-viewer/phase11.css"' in html
    assert 'src="/static/weather-viewer/phase11.js"' in html
    css = (ROOT / "app/static/weather-viewer/phase11.css").read_text(encoding="utf-8")
    assert "backdrop-filter: none !important" in css
    assert "--accent: #246b32" in css
    assert ".weather-scan-indicator" in css


def test_phase11_audio_files_match_release_manifest() -> None:
    manifest = json.loads((ROOT / "manifests/phase11_audio_checksums.json").read_text(encoding="utf-8"))
    import hashlib

    for relative, expected in manifest.items():
        data = (ROOT / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected


def test_phase11_formal_report_presentation_version() -> None:
    assert FORMAL_REPORT_GENERATOR_VERSION == "formal-report-generator-1.1.0"
    assert REPORT_PRESENTATION_VERSION == "official-office-report-1.1.0"
