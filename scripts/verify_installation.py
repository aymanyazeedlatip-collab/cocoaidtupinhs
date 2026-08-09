from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from app.core.config import settings
from app.models.registry import model_metadata, model_runtime_status
from app.storage.database import initialize_database
from app.storage.migrations import MigrationManager
from app.weather.assimilation.repository import summary as weather_storage_summary
from app.data_foundation.seeding import seed_reference_data
from app.data_foundation.repository import summary as data_foundation_summary
from datetime import date
from app.schemas.analysis import FarmSiteForecastRequest, PestRiskRequest, PestSpecificRequest, SuitabilityRequest, SimulationRequest, RehabilitationPlanRequest, RehabilitationHazardInput
from app.services.analysis import pest_assessment, suitability_assessment
from app.math.pest_specific import evaluate_specific_pests
from app.simulation.engine import run_simulation
from app.simulation.farm_site_forecast import generate_farm_site_forecast
from app.gis.analysis import rehabilitation_event_plans

initialize_database()
migration_status = MigrationManager(settings.database_path).status()
assert len(migration_status) >= 5 and migration_status[4].state == "applied", "Phase 5 Bayesian migration is not applied"
weather_counts = weather_storage_summary()["counts"]
assert set(weather_counts) == {"weather_model_runs", "weather_values", "weather_feature_sets", "weather_features"}
seed_reference_data()
phase2_counts = data_foundation_summary()
assert phase2_counts["source_documents"] == 16
assert phase2_counts["coconut_varieties"] == 30
assert phase2_counts["variety_parameters"] == 408
assert phase2_counts["pest_profiles"] == 5
assert phase2_counts["intercrop_candidates"] == 35
assert phase2_counts["canopy_light_parameters"] == 81
assert phase2_counts["fertilization_scenarios"] == 2
assert phase2_counts["intercrop_economic_profiles"] == 3
assert settings.synthetic_data_path.exists(), "Synthetic dataset is missing"
assert settings.climate_demo_path.exists(), "Climate demo dataset is missing"
assert settings.official_production_profiles_path.exists(), "Processed PSA production profiles are missing"
assert (ROOT / "data" / "source" / "COCONUT_PRODUCTION_ALL_PROVINCES_2010_2026_PSA.xlsx").exists(), "PSA source workbook is missing"
models=model_metadata()
assert all(item["available"] for item in models.values()), "One or more model artifacts are missing"
runtime_status=model_runtime_status()
assert runtime_status["expected_scikit_learn"] == "1.9.0"
assert 0 <= pest_assessment(PestRiskRequest())["posterior_probability"] <= 1
assert 0 <= suitability_assessment(SuitabilityRequest())["score"] <= 1

pest_specific=evaluate_specific_pests(PestSpecificRequest())
assert len(pest_specific["pests"]) >= 8
assert all(0 <= item["outbreak_score"] <= 100 for item in pest_specific["pests"])
assert all(
    item["image_url"].startswith("https://")
    or (ROOT / "app" / "static" / item["image_url"].removeprefix("/static/")).exists()
    for item in pest_specific["pests"]
)
assert all((ROOT / "app" / "static" / item["fallback_image_url"].removeprefix("/static/")).exists() for item in pest_specific["pests"])
assert settings.gemini_model == "gemini-flash-latest"
rehab = rehabilitation_event_plans(RehabilitationPlanRequest(
    hazards=[RehabilitationHazardInput(
        event_type="drought", label="Verification drought", start_date=date(2030, 1, 1), end_date=date(2030, 1, 21),
        peak_severity=0.30, loss_percent_of_event_baseline=14.0, estimated_trees_affected=80,
    )],
    rows=8, cols=8,
))
assert len(rehab["plans"]) == 1
assert rehab["plans"][0]["counts"]["Needs inspection"] + rehab["plans"][0]["counts"]["Needs Rehabilitation"] > 0
result=run_simulation(SimulationRequest(runs=100,end_year=2030))
assert result["yearly"] and result["summary"]["final_median_tons"] >= 0
hybrid=generate_farm_site_forecast(FarmSiteForecastRequest(
    start_year=2026, end_year=2027, start_date=date(2026, 7, 19), runs=100,
    include_live_short_term=False,
))
assert hybrid["frames"] and hybrid["frames"][0]["date"] == "2026-07-19"
assert hybrid["timeline_resolution"] == "daily_visual_frames_with_weekly_agricultural_control_points"
assert hybrid["daily_frame_count"] == len(hybrid["daily_frames"])
assert all(abs(row["production_coconut_mature_tons"] + row["production_coconut_young_tons"] - row["production_coconut_w_husk_tons"]) < 2e-5 for row in hybrid["frames"])
assert (ROOT / "app" / "static" / "weather-viewer" / "app.js").exists()
audio_dir = ROOT / "app" / "static" / "assets" / "audio"
required_audio = {
    "bgm-1.mp3", "home.mp3", "farm-setup.mp3", "farm-site-forecast.mp3",
    "extreme-weather.mp3", "farm-health.mp3", "reports.mp3", "database.mp3",
    "about.mp3", "weather-gis.mp3", "forecast-complete.mp3",
}
assert all((audio_dir / name).exists() and (audio_dir / name).stat().st_size > 10_000 for name in required_audio), "One or more audio assets are missing"
print("COCO-AID verification passed")
print(f"API version: {settings.api_version}")
print(f"Models: {', '.join(models)}")
print(f"Model runtime mode: {runtime_status['mode']}")
print(f"Phase 2 reference documents: {phase2_counts['source_documents']}")
print(f"Phase 2 coconut varieties: {phase2_counts['coconut_varieties']}")
print("Phase 3 weather migration: applied")
print("Phase 4 production migration: applied")
print("Phase 5 Bayesian migration: applied")
print(f"Phase 4 intercrop economic profiles: {phase2_counts['intercrop_economic_profiles']}")
if runtime_status["action"]:
    print(f"Runtime action: {runtime_status['action']}")
