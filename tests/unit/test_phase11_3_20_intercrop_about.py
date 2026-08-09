from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
JS = (ROOT / 'app/static/app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/phase11.css').read_text(encoding='utf-8')
STATUS = (ROOT / 'app/interface/status.py').read_text(encoding='utf-8')


def test_11320_version_and_cache_are_consistent():
    assert 'phase11-agritech-interface-1.3.23' in STATUS
    for asset in ('styles.css', 'phase11.css', 'app.js', 'phase11.js'):
        assert f'/static/{asset}?v=11.3.23' in HTML


def test_intercrop_scene_has_performance_guards():
    assert 'intercropSceneLayoutCache' in JS
    assert 'intercropSceneDepthOrderAt' in JS
    assert 'const maxPlants=125' in JS
    assert 'Math.min(1.05,window.devicePixelRatio||1)' in JS
    assert 'now-state.intercropSceneDepthOrderAt>280' in JS
    assert '>=55' in JS
    assert 'shadowBlur=6+10*pulse' not in JS


def test_intercrop_vertical_control_and_zoom_direction_are_explicit():
    assert 'state.intercropCamera.pitch-dy*.006' in JS
    assert 'Math.min(3.6,state.intercropCamera.zoom' in JS
    assert 'Math.max(.26,Math.min(3.6,camera.zoom||1))' in JS


def test_intercrop_photos_never_have_an_unhandled_blank_state():
    assert 'data-intercrop-photo=' in JS
    assert 'installIntercropImageFallbacks' in JS
    assert 'intercropFallbackImage(candidate)' in JS
    assert 'cocoaid-intercrop-photo:' in JS
    assert 'Math.min(4,queue.length||1)' in JS
    assert 'decoding="async"' in JS


def test_about_page_has_interactive_hologram_and_system_explorer():
    for token in (
        'id="aboutHologramCanvas"',
        'id="aboutSystemExplorer"',
        'data-about-module="foundation"',
        'data-about-module="weather"',
        'data-about-module="models"',
        'data-about-module="intercrop"',
        'data-about-module="decision"',
        'Core formula catalogue',
        'Research principles',
    ):
        assert token in HTML
    for token in ('drawAboutHologram', 'setupAboutExperience', 'selectAboutModule', 'aboutHologramLoop'):
        assert token in JS
    for token in ('.about-v2-hero', '.about-hologram-stage', '.about-module-buttons', '.about-card-toggle'):
        assert token in CSS
