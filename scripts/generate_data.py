from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGIONS = [
    ("Region XII", "South Cotabato", 6.33, 124.95, 1.00),
    ("Region XI", "Davao Oriental", 7.30, 126.55, 1.08),
    ("Region VIII", "Leyte", 11.10, 124.85, 1.12),
    ("Region IV-A", "Quezon", 13.95, 121.62, 1.05),
    ("Region IX", "Zamboanga del Sur", 7.80, 123.20, 0.96),
    ("Region V", "Albay", 13.18, 123.55, 1.02),
]
VARIETY_FACTOR = {"Tall": 1.0, "Dwarf": 0.82, "Hybrid": 1.18}
INTERVENTIONS = ["none", "monitoring", "pest_control", "soil_rehabilitation", "replanting", "combined"]


def _membership(value: float, low: float, ideal_low: float, ideal_high: float, high: float) -> float:
    if value <= low or value >= high:
        return 0.0
    if ideal_low <= value <= ideal_high:
        return 1.0
    if value < ideal_low:
        return (value - low) / (ideal_low - low)
    return (high - value) / (high - ideal_high)


def create_synthetic_dataset(path: Path | None = None, seed: int = 20260719, farms: int = 360, years_per_farm: int = 8) -> Path:
    path = path or ROOT / "data" / "synthetic" / "coconut_farm_years.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows = []
    created_at = datetime.now(UTC).isoformat()

    for farm_number in range(farms):
        farm_id = f"SYN-FARM-{farm_number + 1:04d}"
        region, province, base_lat, base_lon, rain_factor = REGIONS[farm_number % len(REGIONS)]
        latitude = base_lat + rng.normal(0, 0.18)
        longitude = base_lon + rng.normal(0, 0.18)
        elevation = float(np.clip(rng.gamma(2.1, 75), 3, 950))
        slope = float(np.clip(abs(rng.normal(5.5 + elevation / 220, 4.0)), 0, 35))
        area = float(np.clip(rng.lognormal(np.log(3.5), 0.55), 0.5, 28))
        tree_density = float(np.clip(rng.normal(135, 18), 85, 180))
        total_trees = int(round(area * tree_density))
        variety = str(rng.choice(["Tall", "Dwarf", "Hybrid"], p=[0.66, 0.13, 0.21]))
        soil_ph = float(np.clip(rng.normal(5.9, 0.65), 4.1, 8.2))
        nitrogen = float(np.clip(rng.beta(3.1, 2.3), 0.08, 0.98))
        phosphorus = float(np.clip(0.75 * nitrogen + 0.25 * rng.beta(2.5, 3.0), 0.05, 0.98))
        potassium = float(np.clip(0.55 * nitrogen + 0.45 * rng.beta(3.0, 2.0), 0.05, 0.99))
        drainage = float(np.clip(0.78 - slope / 80 + rng.normal(0, 0.12), 0.1, 0.98))
        base_age = float(np.clip(rng.normal(33, 14), 4, 72))
        base_productivity_per_palm = float(np.clip(rng.normal(0.028, 0.006), 0.012, 0.045))
        prior_pest = float(np.clip(rng.beta(2.2, 12), 0.015, 0.50))
        prior_yield = None

        for year_offset in range(years_per_farm):
            year = 2018 + year_offset
            age = base_age + year_offset
            seasonal_noise = rng.normal(0, 110)
            rainfall = float(np.clip((2150 * rain_factor) + seasonal_noise + 80 * np.sin(year_offset / 2), 900, 3900))
            temperature = float(np.clip(27.1 - 0.006 * elevation + 0.028 * year_offset + rng.normal(0, 0.35), 22, 32.5))
            humidity = float(np.clip(72 + rainfall / 220 + rng.normal(0, 3.2), 55, 96))
            drought_index = float(np.clip((1800 - rainfall) / 1600 + max(0, temperature - 29) / 5, 0, 1))
            typhoon_exposure = float(np.clip(rng.beta(1.5, 8.0) * (1.25 if province in {"Leyte", "Albay"} else 0.85), 0, 1))
            event_roll = rng.random()
            if event_roll < 0.07 + 0.05 * typhoon_exposure:
                weather_event = "typhoon"
                weather_severity = float(rng.beta(2.0, 2.4))
            elif event_roll < 0.14 + 0.10 * drought_index:
                weather_event = "drought"
                weather_severity = float(rng.beta(2.1, 2.2))
            elif event_roll < 0.21:
                weather_event = "extreme_rain"
                weather_severity = float(rng.beta(1.8, 2.6))
            elif temperature > 29.1 and event_roll < 0.30:
                weather_event = "heat_stress"
                weather_severity = float(rng.beta(2.0, 2.5))
            else:
                weather_event = "normal"
                weather_severity = float(rng.beta(1.5, 5.0))

            intervention = str(rng.choice(INTERVENTIONS, p=[0.28, 0.14, 0.16, 0.14, 0.12, 0.16]))
            pest_control = intervention in {"pest_control", "combined"}
            soil_rehab = intervention in {"soil_rehabilitation", "combined"}
            replanting = intervention in {"replanting", "combined"}

            age_risk = 1 / (1 + np.exp(-(age - 48) / 8))
            pest_linear = -2.2 + 1.1 * (humidity - 75) / 15 + 0.55 * (rainfall - 2000) / 900 + 1.1 * age_risk + 0.8 * typhoon_exposure - (1.25 if pest_control else 0)
            pest_probability = float(1 / (1 + np.exp(-pest_linear)))
            pest_outcome = int(rng.random() < pest_probability)
            severity = int(np.clip(round(3 * (0.45 * pest_outcome + 0.55 * rng.beta(1.5, 3))), 0, 3))
            yellowing = int(pest_outcome and rng.random() < 0.70 or drought_index > 0.55 and rng.random() < 0.35)
            crown_decline = int(pest_outcome and rng.random() < 0.45)
            frond_cuts = int(pest_outcome and rng.random() < 0.32)
            visible_scale = int(pest_outcome and rng.random() < 0.40)
            beetle_damage = int(pest_outcome and rng.random() < 0.30)
            premature_nut_fall = int(pest_outcome and rng.random() < 0.48 or weather_event in {"typhoon", "drought"} and rng.random() < 0.35)
            nearby_reports = int(rng.random() < min(0.85, pest_probability * 1.3))

            aging_share = float(np.clip(0.08 + 0.65 * age_risk + rng.normal(0, 0.04), 0.02, 0.72))
            young_share = float(np.clip(0.08 + (0.12 if replanting else 0) + rng.normal(0, 0.025), 0.02, 0.28))
            dead_share = float(np.clip(0.015 + 0.05 * age_risk + (0.08 * weather_severity if weather_event == "typhoon" else 0), 0.005, 0.25))
            infested_share = float(np.clip(pest_probability * (0.16 if pest_outcome else 0.05), 0, 0.22))
            stressed_share = float(np.clip(0.04 + 0.18 * drought_index + (0.12 * weather_severity if weather_event != "normal" else 0), 0.01, 0.30))
            recovering_share = float(np.clip((0.06 if intervention != "none" else 0.015) + rng.normal(0, 0.015), 0, 0.15))
            productive_share = max(0.03, 1 - sum([aging_share, young_share, dead_share, infested_share, stressed_share, recovering_share]))
            shares = np.array([young_share, productive_share, aging_share, stressed_share, infested_share, recovering_share, dead_share])
            shares = np.clip(shares, 0.002, None)
            shares = shares / shares.sum()
            counts = rng.multinomial(total_trees, shares)

            suitability = (
                0.17 * _membership(rainfall, 800, 1500, 2800, 4300)
                + 0.15 * _membership(temperature, 18, 24, 29, 36)
                + 0.14 * _membership(soil_ph, 4, 5.5, 7.2, 8.6)
                + 0.14 * (nitrogen + phosphorus + potassium) / 3
                + 0.08 * _membership(elevation, -20, 0, 600, 1400)
                + 0.08 * _membership(slope, 0, 0, 12, 35)
                + 0.08 * drainage
                + 0.08 * (1 - drought_index)
                + 0.08 * (1 - typhoon_exposure)
            )
            suitability = float(np.clip(suitability, 0, 1))
            suitability_class = int(np.digitize(suitability, [0.3, 0.5, 0.7, 0.85]))

            climate_factor = np.exp(-0.65 * drought_index - 0.28 * max(0, temperature - 29))
            pest_factor = 1 - (0.20 + 0.20 * severity / 3) * pest_outcome
            event_factor = 1.0
            if weather_event == "typhoon": event_factor -= 0.22 + 0.36 * weather_severity
            elif weather_event == "drought": event_factor -= 0.12 + 0.28 * weather_severity
            elif weather_event == "extreme_rain": event_factor -= 0.05 + 0.15 * weather_severity
            elif weather_event == "heat_stress": event_factor -= 0.08 + 0.18 * weather_severity
            management_factor = 1 + 0.05 * soil_rehab + 0.04 * pest_control + 0.02 * replanting
            productive_equivalent = counts[1] + 0.58 * counts[2] + 0.35 * counts[5]
            production_tons = productive_equivalent * base_productivity_per_palm * VARIETY_FACTOR[variety] * suitability * climate_factor * pest_factor * max(0.25, event_factor) * management_factor
            production_tons *= float(rng.lognormal(-0.5 * 0.09**2, 0.09))
            if prior_yield is not None:
                production_tons = 0.78 * production_tons + 0.22 * prior_yield
            prior_yield = production_tons
            yield_per_ha = production_tons / area
            replanting_survival = float(np.clip(rng.beta(13 + 4 * suitability, 4 + 5 * drought_index), 0.25, 0.99))
            rehabilitation_success = int(
                intervention != "none" and yield_per_ha >= 0.85 * (3.0 * rain_factor) and dead_share < 0.18
            )

            rows.append({
                "record_id": f"{farm_id}-{year}", "farm_id": farm_id, "year": year,
                "region": region, "province": province, "latitude": latitude, "longitude": longitude,
                "elevation_m": elevation, "slope_degrees": slope, "farm_area_hectares": area,
                "tree_density_per_hectare": tree_density, "total_trees": total_trees,
                "young_trees": int(counts[0]), "productive_trees": int(counts[1]), "aging_trees": int(counts[2]),
                "stressed_trees": int(counts[3]), "infested_trees": int(counts[4]), "recovering_trees": int(counts[5]), "dead_trees": int(counts[6]),
                "average_tree_age": age, "variety": variety, "soil_ph": soil_ph,
                "nitrogen_index": nitrogen, "phosphorus_index": phosphorus, "potassium_index": potassium,
                "drainage_index": drainage, "annual_rainfall_mm": rainfall, "mean_temperature_c": temperature,
                "relative_humidity_percent": humidity, "drought_exposure": drought_index,
                "typhoon_exposure": typhoon_exposure, "weather_event": weather_event, "weather_severity": weather_severity,
                "intervention": intervention, "pest_control": int(pest_control), "soil_rehabilitation": int(soil_rehab), "replanting": int(replanting),
                "yellowing": yellowing, "crown_decline": crown_decline, "frond_cuts": frond_cuts,
                "visible_scale_insects": visible_scale, "rhinoceros_beetle_damage": beetle_damage,
                "premature_nut_fall": premature_nut_fall, "nearby_reports": nearby_reports, "symptom_severity": severity,
                "pest_probability": pest_probability, "pest_outcome": pest_outcome,
                "suitability_score": suitability, "suitability_class": suitability_class,
                "annual_production_tons": production_tons, "yield_tons_per_hectare": yield_per_ha,
                "replanting_survival": replanting_survival, "rehabilitation_success": rehabilitation_success,
                "data_source_type": "synthetic_reference_based", "is_synthetic": True,
                "generation_version": "agri-synthetic-1.0", "generation_seed": seed,
                "reference_group": "Philippine coconut development ranges", "created_at": created_at,
                "quality_flag": "development_only",
            })

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)

    default_path = ROOT / "data" / "synthetic" / "coconut_farm_years.csv"
    if path.resolve() == default_path.resolve():
        metadata_dir = ROOT / "data" / "metadata"
        metadata_filename = "GENERATION_REPORT.json"
    else:
        metadata_dir = path.parent
        metadata_filename = f"{path.stem}_GENERATION_REPORT.json"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    required = ["record_id", "farm_id", "data_source_type", "generation_version", "generation_seed", "reference_group", "is_synthetic", "created_at", "quality_flag"]
    validation = {
        "rows": len(df), "farms": int(df.farm_id.nunique()), "years": [int(df.year.min()), int(df.year.max())],
        "required_provenance_present": all(c in df.columns for c in required),
        "negative_rainfall_count": int((df.annual_rainfall_mm < 0).sum()),
        "invalid_probability_count": int(((df.pest_probability < 0) | (df.pest_probability > 1)).sum()),
        "invalid_tree_total_count": int(((df[["young_trees", "productive_trees", "aging_trees", "stressed_trees", "infested_trees", "recovering_trees", "dead_trees"]].sum(axis=1)) != df.total_trees).sum()),
        "seed": seed,
    }
    (metadata_dir / metadata_filename).write_text(json.dumps(validation, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(create_synthetic_dataset())
