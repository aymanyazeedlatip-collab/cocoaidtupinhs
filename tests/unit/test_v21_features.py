from __future__ import annotations

from datetime import date

from app.math.pest_specific import evaluate_specific_pests
from app.schemas.analysis import PestSpecificRequest
from app.schemas.farm import FarmCreate
from app.simulation.farm_site_forecast import (
    _build_extreme_events,
    _weather_adjusted_category_shares,
)


def test_pest_specific_scores_are_bounded_and_symptoms_raise_matching_risk():
    baseline = evaluate_specific_pests(PestSpecificRequest())
    symptomatic_farm = FarmCreate()
    symptomatic_farm.symptoms.visible_scale_insects = True
    symptomatic_farm.symptoms.yellowing = True
    symptomatic_farm.symptoms.nearby_reports = True
    symptomatic_farm.symptoms.severity = 3
    elevated = evaluate_specific_pests(PestSpecificRequest(
        farm=symptomatic_farm,
        temperature_c=28,
        humidity_percent=86,
        rainfall_mm_week=55,
    ))
    assert len(elevated["pests"]) >= 8
    assert all(0 <= item["outbreak_score"] <= 100 for item in elevated["pests"])
    base_scale = next(item for item in baseline["pests"] if item["pest_id"] == "coconut_scale")
    high_scale = next(item for item in elevated["pests"] if item["pest_id"] == "coconut_scale")
    assert high_scale["outbreak_score"] > base_scale["outbreak_score"]
    assert high_scale["image_url"].endswith("coconut-scale-photo.jpg")
    assert high_scale["image_credit"]
    assert high_scale["image_source_url"]
    assert high_scale["ai_recommendations"]


def test_weather_response_changes_mature_and_young_shares_but_conserves_total():
    calibration = {
        "mature_share": 0.92,
        "young_share": 0.08,
        "quarter_shares": {
            "coconut_w_husk": {"q3": 0.25},
            "coconut_mature": {"q3": 0.25},
            "coconut_young": {"q3": 0.25},
        },
    }
    normal = {
        "rainfall_mm": 35, "temperature_c": 27.5, "temperature_max_c": 31,
        "humidity_percent": 80, "wind_speed_kmh": 12, "pest_probability": .10,
        "farm_condition_score": .82, "event_severity": 0, "event": "normal",
    }
    severe = {
        **normal, "rainfall_mm": 250, "temperature_max_c": 37, "wind_speed_kmh": 95,
        "pest_probability": .55, "farm_condition_score": .40,
        "event_severity": .85, "event": "typhoon",
    }
    m1, y1, factors1 = _weather_adjusted_category_shares(calibration, date(2035, 7, 15), normal, 150)
    m2, y2, factors2 = _weather_adjusted_category_shares(calibration, date(2035, 7, 15), severe, 40)
    assert abs((m1 + y1) - 1.0) < 1e-12
    assert abs((m2 + y2) - 1.0) < 1e-12
    assert (m1, y1) != (m2, y2)
    assert factors2["young_weather_factor"] < factors1["young_weather_factor"]


def test_hazard_loss_increases_with_severity_for_same_duration_and_type():
    def frames(severity: float):
        return [
            {
                "event": "heat_stress", "event_severity": severity,
                "week_start": f"2035-04-{1 + 7*i:02d}", "week_end": f"2035-04-{7 + 7*i:02d}",
                "production_coconut_w_husk_tons": 1.2,
                "data_mode": "plausible_stochastic_climate_simulation",
            }
            for i in range(2)
        ]
    low = _build_extreme_events(frames(.3), baseline_annual_tons=100, total_trees=1000)[0]
    high = _build_extreme_events(frames(.8), baseline_annual_tons=100, total_trees=1000)[0]
    assert high["severity_percent"] > low["severity_percent"]
    assert high["estimated_production_loss_tons"] > low["estimated_production_loss_tons"]
    assert high["estimated_trees_affected"] > low["estimated_trees_affected"]


def test_poor_farm_condition_increases_pest_specific_pressure():
    healthy = evaluate_specific_pests(PestSpecificRequest(farm_condition_score=.90))
    weak = evaluate_specific_pests(PestSpecificRequest(farm_condition_score=.25))
    assert weak["overall_outbreak_pressure"] > healthy["overall_outbreak_pressure"]
    assert all("farm_condition_deficit" in item["calculation_terms"] for item in weak["pests"])
