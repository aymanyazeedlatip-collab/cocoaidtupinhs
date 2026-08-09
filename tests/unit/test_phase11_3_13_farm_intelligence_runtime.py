from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
STATUS = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")

def test_removed_health_evidence_cards_are_not_required_by_renderer():
    assert 'class="legacy-health-evidence-compat"' in HTML
    assert '<span class="eyebrow">Bayesian evidence</span>' not in HTML
    assert '<span class="eyebrow">Suitability evidence</span>' not in HTML
    assert 'id="pestEvidenceList"' in HTML
    assert 'id="pestProbabilityBar"' in HTML
    assert 'id="suitabilityFactors"' in HTML
    assert 'const probabilityBar = $("pestProbabilityBar")' in JS
    assert 'if (probabilityBar)' in JS
    assert 'const evidenceList = $("pestEvidenceList")' in JS
    assert 'if (evidenceList)' in JS
    assert 'const suitabilityList = $("suitabilityFactors")' in JS
    assert 'if (suitabilityList)' in JS

def test_pest_specific_failure_does_not_block_core_health_render():
    assert 'Pest-specific risk could not be refreshed; core Farm Health remains available.' in JS
    assert 'state.health = { pest, suit, assessment, rehab, specific }' in JS
    assert 'renderHealth();' in JS

def test_release_version_1313():
    assert 'phase11-agritech-interface-1.3.23' in STATUS
    assert '?v=11.3.23' in HTML
