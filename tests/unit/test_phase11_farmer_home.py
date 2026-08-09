from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_entry_screen_has_no_hologram_and_home_has_the_only_hologram():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    entry = html.split("</section>", 1)[0]
    assert "coconutHologramPreview" not in entry
    assert "holo-coconut-3d" not in entry
    assert html.count('id="coconutHologramWorkspace"') == 1


def test_farmer_home_is_fullscreen_guided_and_has_no_home_logo():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    home = html.split('id="landing"', 1)[1].split('id="farm-setup"', 1)[0]
    assert "farmer-home-hero" in home
    assert "Four steps from farm details to a clear action plan" in home
    assert "Official PSA annual production" in home
    assert "coco-aid-wordmark.png" not in home
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    assert ".farmer-home-hero" in css
    assert "min-height: 100vh" in css


def test_navigation_is_off_canvas_with_single_global_menu_control():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    assert html.count('id="globalNavButton"') == 1
    assert 'id="navigationBackdrop"' not in html
    assert '$("globalNavButton")?.addEventListener' in js
    assert ".sidebar.open { transform: translateX(0); }" in css


def test_phase113_home_uses_full_bleed_background_and_parametric_mesh():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    js = (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
    home = html.split('id="landing"', 1)[1].split('id="farm-setup"', 1)[0]
    assert "Plant Sharper" in home
    assert "Harvest Better" in home
    assert 'class="holo-coconut-mesh"' in home
    assert 'class="home-legacy-support"' in home
    assert 'aria-hidden="true"' in home
    assert 'inert=""' in home or ' inert' in home
    assert "url('/static/assets/brand/coconut-farm-hero.jpg')" in css
    assert ".home-hologram-frame" in css and "background: transparent" in css
    assert "createCoconutMeshRenderer" in js
    assert "coconutPoint" in js
    assert "longitudeCount" in js


def test_phase113_entry_hides_global_menu_until_entered():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    assert '<body class="preview-active">' in html
    assert "body.preview-active .global-menu-button" in css
