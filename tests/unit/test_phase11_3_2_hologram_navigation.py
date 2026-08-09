from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_orbit_lines_and_nodes_are_thick_solid_white():
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    home = html.split('id="landing"', 1)[1].split('id="farm-setup"', 1)[0]
    assert home.count('class="holo-ring ') == 3
    assert "border: 3px solid #ffffff !important" in css
    assert "width: 12px !important" in css
    assert "height: 12px !important" in css
    assert "background: #ffffff !important" in css


def test_hologram_alternates_coconut_and_tree_with_five_second_hold():
    js = (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
    assert 'const coconut = makeModel("coconut", .94)' in js
    assert 'const tree = makeModel("tree", .82)' in js
    assert "const HOLD_MS = 5000" in js
    assert "const TRANSITION_MS = 1250" in js
    assert '"trunk-longitude"' in js
    assert '"frond"' in js
    assert '"leaflet"' in js
    assert "current.name}-to-${next.name}" in js
    assert "drawModel(current" in js and "drawModel(next" in js


def test_menu_is_left_connected_and_no_navigation_backdrop_exists():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert 'id="navigationBackdrop"' not in html
    assert 'button.style.setProperty("left"' in js
    assert 'button.style.setProperty("right", "auto"' in js
    assert 'button.classList.toggle("is-connected", open)' in js
    assert ".global-menu-button.is-connected" in css
    assert "border-radius: 0 13px 13px 0 !important" in css
    assert "state.settings.sidebarCollapsed = !state.settings.sidebarCollapsed" in js


def test_frontend_assets_are_cache_busted():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert "/static/styles.css?v=11.3.23" in html
    assert "/static/phase11.css?v=11.3.23" in html
    assert "/static/app.js?v=11.3.23" in html
    assert "/static/phase11.js?v=11.3.23" in html
