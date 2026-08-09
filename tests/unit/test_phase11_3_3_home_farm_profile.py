from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_home_is_fullscreen_and_scrollable_with_information_sections() -> None:
    html = read("app/static/index.html")
    css = read("app/static/phase11.css")
    for token in (
        'id="homeLearnMore"',
        "From your farm boundary to a practical action plan.",
        "See what matters before it becomes a problem.",
        "Farmer-friendly does not mean less rigorous.",
    ):
        assert token in html
    assert "min-height: 100svh !important" in css
    assert "overflow-y: auto !important" in css
    assert ".home-below-fold" in css


def test_non_home_pages_use_full_bleed_background() -> None:
    css = read("app/static/phase11.css")
    assert ".page:not(.landing-page)" in css
    assert "max-width: none !important" in css
    assert "background-size: cover !important" in css
    assert "border-radius: 0 !important" in css


def test_farmer_profile_preserves_core_backend_field_ids() -> None:
    html = read("app/static/index.html")
    required_ids = (
        "farmName", "region", "province", "municipality", "barangay", "area",
        "latitude", "longitude", "totalTrees", "youngTrees", "productiveTrees",
        "agingTrees", "stressedTrees", "infestedTrees", "recoveringTrees", "deadTrees",
        "averageAge", "variety", "annualProduction", "yieldPerHa", "copraWeight",
        "nutCount", "oilContent", "elevation", "slope", "soilPh", "nitrogen",
        "phosphorus", "potassium", "drainage", "interventionBurden", "farmMap",
        "polygonInfo", "startForecastButton", "saveFarmButton",
    )
    for field_id in required_ids:
        assert html.count(f'id="{field_id}"') == 1, field_id


def test_farmer_profile_has_guided_steps_easy_helpers_and_plain_language_map_tools() -> None:
    html = read("app/static/index.html")
    js = read("app/static/phase11.js")
    for token in (
        'id="farmGuideBanner"', 'data-form-tab="identity"', 'data-form-tab="trees"',
        'data-form-tab="soil"', 'data-form-tab="symptoms"', 'id="farmerTreeCount"',
        'id="applyTreeEstimateButton"', 'id="farmerSlopeChoice"',
        'id="farmerFertilityChoice"', 'id="farmerDrainageChoice"',
        'id="mapPolygonGuideButton"', 'id="mapRectangleGuideButton"',
        "Draw my farm", "Draw a square",
    ):
        assert token in html
    assert "setupFarmerProfileGuide" in js
    assert "identityAutoAdvanced" in js
    assert 'setStep("trees"' in js
    assert '.leaflet-draw-draw-polygon' in js
    assert '.leaflet-draw-draw-rectangle' in js


def test_completed_boundary_uses_orange_focus_and_darkened_basemap() -> None:
    app_js = read("app/static/app.js")
    css = read("app/static/phase11.css")
    assert 'fillColor: farmFocus ? "#ef8500"' in app_js
    assert 'color: farmFocus ? "#ff9f1a"' in app_js
    assert 'className: farmFocus ? "farm-focus-boundary"' in app_js
    assert "#farmMap.farm-boundary-complete .leaflet-tile-pane" in css
    assert "grayscale(1) brightness(.42)" in css


def test_switching_tabs_resets_scroll_after_scrollable_home() -> None:
    app_js = read("app/static/app.js")
    assert 'window.scrollTo({ top: 0, left: 0, behavior: "auto" })' in app_js


def test_phase_1134_cache_busting_is_consistent() -> None:
    html = read("app/static/index.html")
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in html
