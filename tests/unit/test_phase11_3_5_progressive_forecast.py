from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
JS = (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
APP = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def test_home_keeps_same_sections_but_adds_background_data_and_benchmarks():
    assert HTML.count('class="home-intro-section"') == 1
    assert HTML.count('class="home-decision-section"') == 1
    assert HTML.count('class="home-evidence-section"') == 1
    assert HTML.count('class="home-final-cta"') == 1
    assert "home-farmer-data-card" in HTML
    for token in ("150 mm", "32°C", "80%", "38 km/h", "Pest classifier", "Production model"):
        assert token in HTML
    for asset in ("coconut-farm-01.jpg", "coconut-farmer-05.jpg", "coconut-farm-03.jpg", "coconut-farmer-07.jpg"):
        assert asset in CSS


def test_farm_profile_is_map_first_progressive_and_has_no_replant_question():
    assert 'data-workflow-stage="boundary"' in HTML
    assert "showBoundaryStage" in JS and "showDataStage" in JS
    assert ".farm-step-nav { display:none !important; }" in CSS
    assert "returnToFarmMapButton" in HTML
    assert "How much of the farm do you plan to replant?" not in HTML
    assert 'replanting_percent: 0' in APP
    assert "Replanting need is calculated automatically" in HTML


def test_farm_map_has_geodesic_side_dimensions_and_explicit_edit_save():
    assert "map.distance(a, b)" in APP
    assert "formatFarmSideKm" in APP
    assert "farm-side-distance-marker" in APP and "farm-side-distance-marker" in CSS
    assert "Side ${index + 1}" in APP
    assert 'id="mapSaveEditButton"' in HTML
    assert "nativeSave.click()" in JS


def test_loading_screen_has_mini_hologram_and_orange_text():
    assert 'class="coconut-hologram loading-mini-hologram"' in HTML
    assert 'class="loading-status-text" id="loadingText"' in HTML
    assert ".loading-status-text" in CSS and "#ff9b21" in CSS
    assert ".minimalist-loading .loading-tip" in CSS and "#ffb85f" in CSS


def test_productivity_is_long_term_automatic_and_labels_weather_sources():
    assert "Long-Term Model Forecast" in HTML
    assert "forecastScenario" not in HTML
    assert "forecastIntervention" not in HTML
    assert "forecastRuns" not in HTML
    assert 'AUTO_FORECAST_SCENARIO = "ssp245"' in APP
    assert 'AUTO_FORECAST_INTERVENTION = "combined_rehabilitation"' in APP
    assert "AUTO_FORECAST_RUNS = 1000" in APP
    assert "Open-Meteo numerical forecast" in HTML
    assert "COCOAID climate-conditioned modeled weather" in HTML
    assert "OPEN-METEO · HOURLY FORECAST" in APP
    assert "LONG-TERM · DAILY MODELLED WEATHER" in APP


def test_productivity_uses_local_map_controls_without_duplicate_weather_gis_embed():
    assert 'id="forecastWeatherViewerFrame"' not in HTML
    assert "16-Day Weather GIS &amp; Layer Controls" not in HTML
    assert 'id="forecastMiniWeatherControl"' in HTML
    assert "padding: [92, 92]" in APP
    assert "maxZoom: 16" in APP
    assert "fitForecastMapToFarm(true)" in APP


def test_version_bumped_and_assets_cache_busted():
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML


def test_start_forecast_is_locked_until_guided_workflow_finishes():
    assert 'disabled="" id="startForecastButton"' in HTML
    assert 'Complete Farm Setup First' in HTML
    assert 'function updateForecastGate()' in JS
    assert 'hasBoundary() && steps.every(isCompleted)' in JS
    assert 'startForecastButton.disabled = !ready' in JS
    assert 'if (!identityReady()) return;' in JS
    assert 'if (!treesReady()) return;' in JS
    assert 'if (!soilReady()) return;' in JS


def test_loading_hologram_starts_with_mature_coconut_and_text_is_orange():
    assert 'loading-mini-hologram" data-hologram-start-offset-ms="0"' in HTML
    assert 'id="loadingSegmentBar"' in HTML
    assert 'function updateLoadingSegments' in APP
    assert '.loading-status-text' in CSS
    assert '#ff9b21' in CSS


def test_forecast_timeline_explains_provider_and_modeled_ranges():
    assert 'id="forecastTimelineStrip"' in HTML
    assert 'DAY 1–16' in HTML
    assert 'Open-Meteo numerical forecast' in HTML
    assert 'DAY 17 → 2050' in HTML
    assert 'climate-conditioned modeled weather' in HTML
    assert 'timelineStrip.dataset.sourceMode' in APP


def test_forecast_map_has_compact_weather_controls_and_real_frame_values():
    assert 'id="forecastMiniWeatherControl"' in HTML
    for layer in ('rain', 'wind', 'satellite', 'farm'):
        assert f'data-forecast-map-layer="{layer}"' in HTML
    for field in ('forecastMiniRain','forecastMiniTemp','forecastMiniHumidity','forecastMiniCloud','forecastMiniWind'):
        assert f'id="{field}"' in HTML
    assert 'renderForecastWind' in APP
    assert 'wind_direction_grid' in APP and 'f.wind_direction_deg' in APP
    assert 'f.humidity_percent' in APP
    assert 'f.cloud_cover_percent' in APP
    assert 'setForecastMapLayer' in APP


def test_drawn_farm_auto_frames_to_polygon_size():
    assert 'function fitDrawMapToFarm(source = "farm")' in APP
    assert 'map.fitBounds(bounds' in APP
    assert 'setTimeout(() => fitDrawMapToFarm(source), 80)' in APP


def test_farmer_facing_settings_remove_manual_scenario_strategy_run_inputs():
    assert 'Long-term forecast configuration is automatic' in HTML
    assert 'legacy-auto-forecast-settings" hidden' in HTML
    assert 'Default climate scenario' not in HTML
    assert 'Default rehabilitation strategy' not in HTML
    assert 'Default simulation runs' not in HTML
