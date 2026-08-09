from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / 'app/static/index.html').read_text(encoding='utf-8')
CSS = (ROOT / 'app/static/phase11.css').read_text(encoding='utf-8')
PHASE11 = (ROOT / 'app/static/phase11.js').read_text(encoding='utf-8')
STATUS = (ROOT / 'app/interface/status.py').read_text(encoding='utf-8')
VOICE = (ROOT / 'TAB_VOICELINE_SCRIPTS_PHASE_11_3_21.md').read_text(encoding='utf-8')


def test_11321_version_and_cache_are_consistent():
    assert 'phase11-agritech-interface-1.3.23' in STATUS
    for asset in ('styles.css', 'phase11.css', 'app.js', 'phase11.js'):
        assert f'/static/{asset}?v=11.3.23' in HTML


def test_mature_coconut_shape_is_retained_but_white_and_slightly_smaller():
    assert 'const coconut = makeModel("coconut", .94);' in PHASE11
    assert 'const coconutPoint = (u, v) =>' in PHASE11
    assert 'context.strokeStyle = `rgba(255,255,255,' in PHASE11
    assert 'context.fillStyle = "rgba(255,255,255,.98)";' in PHASE11
    assert 'matureCoconut' not in PHASE11
    assert 'rgba(255,171,77,.25)' not in CSS
    assert 'rgba(255,174,83,.30)' not in CSS


def test_about_hologram_uses_logo_core_and_connectors():
    assert '<div class="about-holo-core"><img alt="COCO-AID logo" src="/static/assets/brand/coco-aid-logo-192.png"/></div>' in HTML
    assert 'COCO-AID</b><small>DECISION SYSTEM' not in HTML
    assert 'class="about-holo-connectors"' in HTML
    assert HTML.count('<line x1=') >= 4
    assert '.about-holo-connectors line' in CSS
    assert '@keyframes aboutConnectorFlow' in CSS


def test_voice_line_script_covers_every_user_facing_destination():
    headings = (
        '## Home', '## Farm Profile', '## Long-Term Weather Forecast',
        '## Extreme Weather Events', '## Intercropping Potential',
        '## Farm Rehabilitation', '## Pest Risk Analysis',
        '## Decision Support Network', '## Farm Database',
        '## Assisted Report Generation', '## About', '## Weather GIS',
    )
    for heading in headings:
        assert heading in VOICE
