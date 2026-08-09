from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HTML=(ROOT/"app/static/index.html").read_text(encoding="utf-8")
JS=(ROOT/"app/static/app.js").read_text(encoding="utf-8")
CSS=(ROOT/"app/static/phase11.css").read_text(encoding="utf-8")
RUNNER=(ROOT/"app/workflows/auto_phase_runner.py").read_text(encoding="utf-8")
PHASE9=(ROOT/"scripts/run_phase9_workflow.py").read_text(encoding="utf-8")

def test_intercropping_tab_and_3d_workspace_exist():
    assert 'data-section="intercropping"' in HTML
    assert 'id="intercrop3dCanvas"' in HTML
    assert 'id="intercropCanopySlider"' in HTML
    assert 'id="intercropCardDeck"' in HTML
    assert 'function drawIntercropScene' in JS
    assert 'function drawCoconutTree3D' in JS
    assert 'function drawIntercrop3D' in JS

def test_intercropping_uses_project_candidate_api_and_dynamic_ranking():
    assert '/api/v2/intercropping/candidates' in JS
    assert '/api/v2/intercropping/assessments?limit=1000' in JS
    assert 'function intercropCanopyFit' in JS
    assert 'function renderIntercroppingWorkspace' in JS
    assert 'intercropCanopyChart' in JS

def test_auto_phase9_assesses_full_intercrop_catalog():
    assert '--all-intercrops' in RUNNER
    assert '--all-intercrops' in PHASE9
    assert 'intercrop_request["candidate_ids"] = []' in PHASE9

def test_hazard_arrow_no_longer_scrolls_event_into_view():
    block=JS[JS.index('function changeHazardEvent'):JS.index('function hazardFirstAction')]
    assert 'highlightHazard(state.hazardIndex, { scroll: false })' in block

def test_rehab_cells_overlap_slightly_to_remove_seams_but_remain_polygon_clipped():
    assert 'padLat=Math.max((north-south)*0.018' in JS
    assert 'padLng=Math.max((east-west)*0.018' in JS
    assert 'clipFarmPolygonToCell' in JS
    assert 'fillOpacity: .82' in JS

def test_intercrop_ui_styles_are_responsive():
    for token in ('.intercrop-workspace-grid','.intercrop-scene-shell','.intercrop-card-deck','.intercrop-score-ring'):
        assert token in CSS
