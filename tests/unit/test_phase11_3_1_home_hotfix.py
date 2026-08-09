from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_hologram_has_no_visible_annotation_text_and_uses_bright_mesh():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
    home = html.split('id="landing"', 1)[1].split('id="farm-setup"', 1)[0]
    assert "DIGITAL TWIN ONLINE" not in home
    assert "Drag to inspect" not in home
    assert "WEATHER</span>" not in home
    assert "Drag to rotate" not in home
    assert 'class="holo-coconut-mesh"' in home
    assert 'const coconut = makeModel("coconut", .94);' in js
    assert 'context.strokeStyle = `rgba(255,255,255,' in js
    assert 'rgba(255,174,84,.82)' not in js


def test_home_orbit_rings_are_white_without_changing_ring_structure():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    home = html.split('id="landing"', 1)[1].split('id="farm-setup"', 1)[0]
    assert home.count('class="holo-ring ') == 3
    assert ".home-hologram-frame .holo-ring" in css
    assert "border: 3px solid #ffffff !important" in css
    assert "background: #ffffff !important" in css


def test_global_menu_is_left_connected_non_blocking_and_icon_collapsible():
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert "left: 24px !important" in css
    assert "body.navigation-open:not(.sidebar-collapsed) .global-menu-button" in css
    assert "body.navigation-open.sidebar-collapsed .global-menu-button" in css
    assert "pointer-events: none !important" in css
    assert "width: 78px !important" in css
    assert "function toggleGlobalNavigation()" in js
    assert "state.settings.sidebarCollapsed = !state.settings.sidebarCollapsed" in js
    assert 'document.addEventListener("pointerdown"' in js
    assert 'setNavigationOpen(true, { forceExpanded: true })' in js
