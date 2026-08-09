from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HTML=(ROOT/"app/static/index.html").read_text(encoding="utf-8")
JS=(ROOT/"app/static/app.js").read_text(encoding="utf-8")
CSS=(ROOT/"app/static/phase11.css").read_text(encoding="utf-8")

def test_single_tabs_are_direct_and_not_expandable():
    assert 'class="nav-direct-item nav-item active" data-section="landing"' in HTML
    assert 'class="nav-direct-item nav-item" data-section="farm-setup"' in HTML
    assert 'class="nav-direct-item nav-item" data-section="about"' in HTML
    assert 'data-nav-group="home"' not in HTML
    assert 'data-nav-group="farm-profile"' not in HTML
    assert 'data-nav-group="about-group"' not in HTML
    assert '>Methodology<' not in HTML

def test_only_expected_groups_expand():
    assert HTML.count('data-nav-group-toggle=') == 3
    assert 'Production Forecast' in HTML
    assert 'Farm Intelligence' in HTML
    assert 'Farm Operations Planning' in HTML

def test_subtabs_use_monochrome_svg_icons_not_pings():
    assert HTML.count('class="nav-subicon"') == 8
    assert '<span class="nav-subdot">' not in HTML
    assert '.nav-subicon svg' in CSS

def test_duplicate_weather_button_removed():
    assert 'id="weatherFloatingButton"' not in HTML
    assert 'weatherFloatingButton' not in JS

def test_long_labels_are_not_clipped():
    assert 'white-space:normal !important' in CSS
    assert 'overflow-wrap:anywhere' in CSS
    assert '--phase11-nav-expanded-width: 316px' in CSS
