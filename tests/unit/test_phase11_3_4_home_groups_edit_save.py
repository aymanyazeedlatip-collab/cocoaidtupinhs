from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

def read(rel): return (ROOT / rel).read_text(encoding="utf-8")

def test_home_reuses_existing_farm_photos_without_adding_sections():
    html=read("app/static/index.html"); css=read("app/static/phase11.css")
    assert html.count('class="home-intro-section"') == 1
    assert html.count('class="home-decision-section"') == 1
    assert html.count('class="home-evidence-section"') == 1
    assert html.count('class="home-final-cta"') == 1
    for asset in ("coconut-farm-01.jpg","coconut-farmer-05.jpg","coconut-farm-03.jpg","coconut-farmer-07.jpg"):
        assert asset in css

def test_home_shows_project_coverage_and_truthful_development_metrics():
    html=read("app/static/index.html")
    for token in ("16 days","30","35","Pest classifier","99.7%","0.928","0.518","400","synthetic/reference-based development data","Real-world validation"):
        assert token in html

def test_four_farm_tabs_now_have_grouped_explanatory_blocks():
    html=read("app/static/index.html")
    assert html.count('class="farm-input-group"') >= 14
    for title in ("Give the farm a name","Tell us where the farm is","Sort the palms by what condition they are in","Add the production you already know","Describe the land and drainage","Describe the soil fertility","Tell us what care the farm receives","Look at the leaves and crown","Look for obvious pest damage","Give one overall severity estimate"):
        assert title in html

def test_all_backend_farm_ids_remain_unique_after_grouping():
    html=read("app/static/index.html")
    ids=("farmName","region","province","municipality","barangay","area","latitude","longitude","totalTrees","youngTrees","productiveTrees","agingTrees","stressedTrees","infestedTrees","recoveringTrees","deadTrees","averageAge","variety","annualProduction","yieldPerHa","copraWeight","nutCount","oilContent","elevation","slope","soilPh","nitrogen","phosphorus","potassium","drainage","interventionBurden","symptomYellowing","symptomCrownDecline","symptomFrondCuts","symptomScale","symptomBeetle","symptomNutFall","symptomNearby","symptomSeverity")
    for field in ids: assert html.count(f'id="{field}"') == 1, field

def test_map_edit_has_large_dedicated_save_control_wired_to_leaflet_save():
    html=read("app/static/index.html"); js=read("app/static/phase11.js"); css=read("app/static/phase11.css")
    assert 'id="mapSaveEditButton"' in html
    assert "Save Farm Shape Changes" in html
    assert 'findLeafletEditAction("Save")' in js
    assert 'nativeSave.click()' in js
    assert 'farm-boundary-editing' in css

def test_phase_1134_versions_are_consistent():
    html=read("app/static/index.html")
    for asset in ("styles.css","phase11.css","app.js","phase11.js"): assert f"/static/{asset}?v=11.3.23" in html
    catalog=json.loads(read("manifests/phase11_interface_catalog.json"))
    assert catalog["version"] == "phase11-agritech-interface-1.3.23"
