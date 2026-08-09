from __future__ import annotations

import json
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURES = ROOT / "tests" / "fixtures" / "reference_farms"
OUTPUTS = ROOT / "baseline_snapshots" / "reference_outputs"


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def response_json(client, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} failed with {response.status_code}: {response.text[:1000]}")
    return response.json()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="cocoaid-phase0-") as temp:
        runtime = Path(temp)
        from app.core.config import settings

        settings.database_path = runtime / "baseline.sqlite3"
        settings.reports_dir = runtime / "reports"
        settings.cache_dir = runtime / "cache"
        settings.offline_mode = True

        from fastapi.testclient import TestClient
        from app.main import app

        OUTPUTS.mkdir(parents=True, exist_ok=True)
        with TestClient(app) as client:
            system = {
                "health": response_json(client, "GET", "/api/health"),
                "config": response_json(client, "GET", "/api/config"),
                "sources": response_json(client, "GET", "/api/sources"),
                "models": response_json(client, "GET", "/api/models"),
                "official_data_summary": response_json(client, "GET", "/api/official-data/summary"),
                "database_summary_before": response_json(client, "GET", "/api/database/summary"),
            }
            write_json(OUTPUTS / "system_baseline.json", system)

            index = []
            for fixture_path in sorted(FIXTURES.glob("*.json")):
                if fixture_path.name == "README.md":
                    continue
                farm = json.loads(fixture_path.read_text(encoding="utf-8"))
                slug = fixture_path.stem
                pest_request = {
                    "prior_probability": 0.15,
                    "symptoms": farm["symptoms"],
                    "humidity_percent": 78,
                    "rainfall_mm_month": 150,
                    "average_tree_age": farm["trees"]["average_age_years"],
                    "confirmed_positive_reports": 0,
                    "confirmed_negative_reports": 0,
                }
                specific_request = {
                    "farm": farm,
                    "temperature_c": 28,
                    "humidity_percent": 82,
                    "rainfall_mm_week": 45,
                    "wind_speed_kmh": 14,
                    "farm_condition_score": 0.6,
                }
                suitability_request = {
                    "soil_terrain": farm["soil_terrain"],
                    "annual_rainfall_mm": 2200,
                    "mean_temperature_c": 27,
                    "humidity_percent": 78,
                    "drought_exposure": 0.18,
                    "climate_stress": 0.15,
                }
                simulation_request = {
                    "farm": farm,
                    "start_year": 2026,
                    "end_year": 2030,
                    "scenario": "ssp245",
                    "intervention": "combined_rehabilitation",
                    "runs": 100,
                    "seed": 42,
                }
                full_request = {
                    "farm": farm,
                    "scenario": "ssp245",
                    "period": "2041-2060",
                    "end_year": 2030,
                    "runs": 100,
                    "seed": 42,
                }
                forecast_request = {
                    "farm": farm,
                    "start_year": 2026,
                    "end_year": 2028,
                    "start_date": "2026-08-03",
                    "scenario": "ssp245",
                    "intervention": "combined_rehabilitation",
                    "runs": 100,
                    "seed": 42,
                    "include_live_short_term": False,
                }
                result = {
                    "fixture": fixture_path.name,
                    "farm": farm,
                    "pest_risk": response_json(client, "POST", "/api/pest-risk/evaluate", json=pest_request),
                    "pest_specific": response_json(client, "POST", "/api/pest-risk/specific", json=specific_request),
                    "suitability": response_json(client, "POST", "/api/suitability/evaluate", json=suitability_request),
                    "simulation": response_json(client, "POST", "/api/simulation/run", json=simulation_request),
                    "full_analysis": response_json(client, "POST", "/api/analysis/full", json=full_request),
                    "farm_site_forecast": response_json(client, "POST", "/api/farm-site/forecast", json=forecast_request),
                }
                output_path = OUTPUTS / f"{slug}_baseline.json"
                write_json(output_path, result)
                overview = result["full_analysis"].get("overview", {})
                sim_summary = result["simulation"].get("summary", {})
                index.append({
                    "fixture": fixture_path.name,
                    "output": output_path.name,
                    "recommended_intervention": overview.get("recommended_intervention"),
                    "projected_end_median_tons": overview.get("projected_end_median_tons"),
                    "simulation_final_median_tons": sim_summary.get("final_median_tons"),
                    "pest_posterior_probability": result["pest_risk"].get("posterior_probability"),
                    "suitability_score": result["suitability"].get("score"),
                })
            write_json(OUTPUTS / "index.json", index)
            write_json(OUTPUTS / "database_summary_after.json", response_json(client, "GET", "/api/database/summary"))

    print(f"Captured baseline outputs for {len(index)} reference farms in {OUTPUTS}")


if __name__ == "__main__":
    main()
