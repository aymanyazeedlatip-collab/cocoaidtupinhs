from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from app.schemas.analysis import PestSpecificRequest


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-float(np.clip(value, -30.0, 30.0))))


def _triangle(value: float, low: float, optimum: float, high: float) -> float:
    """Continuous 0-1 suitability around an optimum."""
    if value <= low or value >= high:
        return 0.0
    if value <= optimum:
        return (value - low) / max(1e-9, optimum - low)
    return (high - value) / max(1e-9, high - optimum)


def _risk_class(score: float) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Moderate"
    if score < 75:
        return "High"
    return "Critical"


@dataclass(frozen=True)
class PestProfile:
    pest_id: str
    common_name: str
    scientific_name: str
    image_url: str
    prior: float
    temp_optimum: tuple[float, float, float]
    humidity_optimum: tuple[float, float, float]
    rain_mode: str
    age_weight: float
    stress_weight: float
    symptom_weights: dict[str, float]
    recommendations: tuple[str, ...]
    affected_part: str
    characteristic_signs: str


PESTS: tuple[PestProfile, ...] = (
    PestProfile(
        "rhinoceros_beetle", "Coconut rhinoceros beetle", "Oryctes rhinoceros",
        "/static/assets/pests/rhinoceros-beetle-photo.png", 0.13, (21, 28, 35), (48, 76, 98), "moderate",
        0.22, 0.35, {"rhinoceros_beetle_damage": 2.1, "frond_cuts": 1.0, "crown_decline": 0.45, "nearby_reports": 0.8},
        (
            "Inspect the crown and unopened spear leaves for fresh V-shaped cuts and boring damage.",
            "Remove or properly manage decaying logs, manure piles, and other breeding material near the farm.",
            "Use monitoring or pheromone traps only according to current local agricultural guidance.",
            "Report clustered or severe damage to the Philippine Coconut Authority or local agriculture office.",
        ),
        "Crown, spear leaves, and young palms", "V-shaped frond cuts, holes in the crown, damaged growing point",
    ),
    PestProfile(
        "coconut_scale", "Coconut scale insect", "Aspidiotus rigidus",
        "/static/assets/pests/coconut-scale-photo.jpg", 0.11, (22, 28, 34), (58, 82, 100), "humid",
        0.15, 0.48, {"visible_scale_insects": 2.6, "yellowing": 0.85, "crown_decline": 0.8, "nearby_reports": 1.0},
        (
            "Inspect the underside of fronds and nearby palms for white scale colonies and yellowing.",
            "Avoid transporting infested leaves or planting material to unaffected areas.",
            "Conserve natural enemies and avoid unnecessary broad-spectrum pesticide use.",
            "Seek PCA or LGU confirmation before applying any registered control product.",
        ),
        "Leaflets and fronds", "White scale colonies, chlorosis, drying leaves, weakened crown",
    ),
    PestProfile(
        "brontispa", "Coconut leaf beetle", "Brontispa longissima",
        "/static/assets/pests/brontispa-photo.jpg", 0.09, (22, 29, 36), (55, 80, 100), "humid",
        0.05, 0.35, {"frond_cuts": 0.65, "crown_decline": 1.25, "yellowing": 0.55, "nearby_reports": 0.95},
        (
            "Inspect unopened spear leaves for feeding scars, larvae, or adult beetles.",
            "Remove and safely dispose of heavily infested leaf material when advised by extension personnel.",
            "Protect parasitoids and other biological-control agents used in local programs.",
            "Prioritize young palms because severe spear-leaf damage can slow establishment.",
        ),
        "Unopened spear leaves and young fronds", "Brown feeding scars, damaged spear leaves, reduced leaf opening",
    ),
    PestProfile(
        "red_palm_weevil", "Red palm weevil", "Rhynchophorus ferrugineus",
        "/static/assets/pests/red-palm-weevil-photo.jpg", 0.07, (20, 29, 37), (45, 75, 98), "moderate",
        0.18, 0.7, {"crown_decline": 1.55, "rhinoceros_beetle_damage": 1.2, "premature_nut_fall": 0.4, "nearby_reports": 0.9},
        (
            "Inspect wounds, trunk bases, and crowns for holes, fermented odor, fibers, or oozing sap.",
            "Avoid unnecessary trunk injuries and seal or manage fresh wounds according to local guidance.",
            "Use approved monitoring traps where a local surveillance program exists.",
            "Isolate and report severely affected palms promptly because internal damage may be advanced before symptoms appear.",
        ),
        "Trunk, crown, and internal tissues", "Bore holes, chewed fibers, oozing sap, crown collapse",
    ),
    PestProfile(
        "eriophyid_mite", "Coconut eriophyid mite", "Aceria guerreronis",
        "/static/assets/pests/eriophyid-mite-photo.jpg", 0.10, (23, 29, 36), (45, 72, 94), "dry_warm",
        0.04, 0.28, {"premature_nut_fall": 1.75, "yellowing": 0.25, "nearby_reports": 0.55},
        (
            "Inspect young nuts beneath the perianth for corky scars, deformation, and premature drop.",
            "Maintain balanced nutrition and reduce prolonged moisture stress where possible.",
            "Remove badly damaged fallen nuts from the immediate monitoring area.",
            "Consult agricultural extension personnel before considering any registered acaricide treatment.",
        ),
        "Young nuts beneath the perianth", "Corky triangular scars, distorted nuts, premature nut fall",
    ),
    PestProfile(
        "black_headed_caterpillar", "Coconut black-headed caterpillar", "Opisina arenosella",
        "https://databases.nbair.res.in/insectpests/thumbnails/Opisina-arenosella1.jpg", 0.08, (22, 29, 37), (42, 68, 92), "dry_warm",
        0.08, 0.45, {"yellowing": 0.55, "crown_decline": 0.75, "frond_cuts": 0.35, "nearby_reports": 0.8},
        (
            "Inspect lower fronds for silk galleries, dried leaflet patches, larvae, and frass.",
            "Remove heavily damaged fronds only when agronomically justified; excessive pruning can further weaken palms.",
            "Conserve parasitoids and predators and coordinate area-wide monitoring when outbreaks cluster.",
            "Escalate expanding defoliation to the local agriculture office for identification and control advice.",
        ),
        "Leaflets, often lower fronds", "Silken galleries, brown patches, frass, progressive defoliation",
    ),
    PestProfile(
        "leaf_miner", "Coconut leaf miner", "Promecotheca cumingii",
        "/static/assets/pests/leaf-miner-photo.jpg", 0.06, (22, 28, 35), (55, 80, 100), "humid",
        0.06, 0.32, {"yellowing": 0.5, "crown_decline": 0.55, "nearby_reports": 0.7},
        (
            "Inspect leaflets for narrow mines or transparent feeding tracks.",
            "Record the fraction of affected fronds and whether damage is increasing between inspections.",
            "Protect natural enemies and avoid unnecessary pesticide applications that may disrupt them.",
            "Submit samples or clear photographs to extension personnel when identification is uncertain.",
        ),
        "Leaflets", "Linear mines, translucent tracks, browning of mined leaf tissue",
    ),
    PestProfile(
        "mealybug", "Coconut mealybug complex", "Pseudococcidae spp.",
        "/static/assets/pests/mealybug-photo.jpg", 0.08, (21, 28, 35), (55, 79, 98), "humid",
        0.02, 0.42, {"visible_scale_insects": 0.95, "yellowing": 0.6, "nearby_reports": 0.55},
        (
            "Inspect leaf axils and tender tissues for white waxy insects, honeydew, and sooty mold.",
            "Monitor and manage ant activity because ants can protect sap-feeding pests from natural enemies.",
            "Improve sanitation and avoid moving infested planting material.",
            "Confirm the pest and any registered treatment with local extension or PCA personnel.",
        ),
        "Leaf axils, tender shoots, and developing nuts", "White waxy colonies, honeydew, ants, sooty mold",
    ),
)


PEST_IMAGE_METADATA: dict[str, dict[str, str]] = {
    "rhinoceros_beetle": {
        "fallback": "/static/assets/pests/rhinoceros-beetle.svg",
        "credit": "Slunky / iNaturalist, CC BY 4.0, via Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Oryctes_rhinoceros_posterior_(384687195).png",
        "license": "CC BY 4.0",
    },
    "coconut_scale": {
        "fallback": "/static/assets/pests/coconut-scale.svg",
        "credit": "Gilles San Martin, CC BY-SA 2.0, via Wikimedia Commons; representative scale-insect photograph",
        "source_url": "https://commons.wikimedia.org/wiki/File:Scale_Insects_(2127992762).jpg",
        "license": "CC BY-SA 2.0",
    },
    "brontispa": {
        "fallback": "/static/assets/pests/brontispa.svg",
        "credit": "Cameron Brumley, DAFWA, CC BY 3.0 AU, via Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Brontispa_longissima.jpg",
        "license": "CC BY 3.0 AU",
    },
    "red_palm_weevil": {
        "fallback": "/static/assets/pests/red-palm-weevil.svg",
        "credit": "gailhampshire, CC BY 2.0, via Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Red_Palm_Weevil,_Rhynchophorus_ferrugineus_-_Flickr_-_gailhampshire.jpg",
        "license": "CC BY 2.0",
    },
    "eriophyid_mite": {
        "fallback": "/static/assets/pests/eriophyid-mite.svg",
        "credit": "Hartford H. Keifer; public-domain coconut mite damage photograph, via Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Coconuts_injured_by_Eriophyes_guerreronis.jpg",
        "license": "Public domain",
    },
    "black_headed_caterpillar": {
        "fallback": "/static/assets/pests/black-headed-caterpillar.svg",
        "credit": "Close-up larval reference from ICAR-National Bureau of Agricultural Insect Resources (NBAIR)",
        "source_url": "https://databases.nbair.res.in/insectpests/Opisina-arenosella.php",
        "license": "External reference image; copyright remains with ICAR-NBAIR",
    },
    "leaf_miner": {
        "fallback": "/static/assets/pests/leaf-miner.svg",
        "credit": "C. L. Staines / USDA; public-domain photograph, via Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Promecotheca_cumingii.jpg",
        "license": "Public domain (US Government work)",
    },
    "mealybug": {
        "fallback": "/static/assets/pests/mealybug.svg",
        "credit": "Nayana.sondi; public-domain representative mealybug photograph, via Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:MealyBug1.jpg",
        "license": "Public domain",
    },
}


def _rain_score(mode: str, rainfall_week: float, humidity: float, temperature: float) -> float:
    if mode == "humid":
        return float(np.clip(0.45 * _triangle(rainfall_week, 2, 45, 220) + 0.55 * _triangle(humidity, 45, 84, 100), 0, 1))
    if mode == "dry_warm":
        dryness = float(np.clip((45.0 - rainfall_week) / 45.0, 0, 1))
        warmth = _triangle(temperature, 23, 30, 39)
        return float(np.clip(0.6 * dryness + 0.4 * warmth, 0, 1))
    return float(np.clip(_triangle(rainfall_week, 0, 35, 180), 0, 1))


def evaluate_specific_pests(request: PestSpecificRequest) -> dict[str, Any]:
    farm = request.farm
    symptoms = farm.symptoms.model_dump()
    total = max(1, farm.trees.total_trees)
    stress_ratio = (farm.trees.stressed + farm.trees.infested + farm.trees.dead) / total
    aging_ratio = farm.trees.aging / total
    protection = 0.0
    if farm.management.monitoring_activity:
        protection += 0.10
    if farm.management.pest_control:
        protection += 0.22
    if farm.management.soil_rehabilitation:
        protection += 0.04

    results: list[dict[str, Any]] = []
    for profile in PESTS:
        temp_score = _triangle(request.temperature_c, *profile.temp_optimum)
        humidity_score = _triangle(request.humidity_percent, *profile.humidity_optimum)
        moisture_score = _rain_score(profile.rain_mode, request.rainfall_mm_week, request.humidity_percent, request.temperature_c)
        symptom_signal = 0.0
        symptom_details: list[str] = []
        for field, weight in profile.symptom_weights.items():
            raw = symptoms.get(field)
            active = float(bool(raw))
            symptom_signal += active * weight
            if active:
                symptom_details.append(field.replace("_", " ").title())
        symptom_signal += farm.symptoms.severity * 0.28
        climate_signal = 0.48 * temp_score + 0.34 * humidity_score + 0.42 * moisture_score
        condition_vulnerability = float(np.clip(1.0 - request.farm_condition_score, 0.0, 1.0))
        vulnerability_signal = (
            profile.age_weight * aging_ratio * 3.0
            + profile.stress_weight * stress_ratio * 3.0
            + 0.45 * condition_vulnerability
        )
        nearby_signal = 0.55 if farm.symptoms.nearby_reports else 0.0
        wind_injury_signal = 0.28 * float(np.clip((request.wind_speed_kmh - 45) / 70, 0, 1)) if profile.pest_id == "red_palm_weevil" else 0.0
        prior_logit = math.log(profile.prior / (1 - profile.prior))
        logit = (
            prior_logit
            + 1.15 * climate_signal
            + vulnerability_signal
            + symptom_signal
            + nearby_signal
            + wind_injury_signal
            - protection
        )
        probability = _sigmoid(logit)
        score = float(np.clip(probability * 100.0, 0, 100))
        drivers = [
            {"name": "Temperature suitability", "value": round(temp_score * 100, 1)},
            {"name": "Humidity suitability", "value": round(humidity_score * 100, 1)},
            {"name": "Moisture pattern", "value": round(moisture_score * 100, 1)},
            {"name": "Farm vulnerability", "value": round(float(np.clip(vulnerability_signal / 2.25, 0, 1)) * 100, 1)},
            {"name": "Farm condition deficit", "value": round(condition_vulnerability * 100, 1)},
            {"name": "Observed symptom signal", "value": round(float(np.clip(symptom_signal / 3.0, 0, 1)) * 100, 1)},
        ]
        recommendations = list(profile.recommendations)
        if score >= 75:
            recommendations.insert(0, "Treat this as an urgent inspection priority and seek confirmatory identification before control action.")
        elif score >= 50:
            recommendations.insert(0, "Increase inspection frequency and document symptoms with dated photographs or sample counts.")
        elif score >= 25:
            recommendations.insert(0, "Maintain routine scouting and compare the same palms at the next inspection.")
        else:
            recommendations.insert(0, "Maintain baseline monitoring; the current conditions do not indicate a high outbreak signal.")
        image_meta = PEST_IMAGE_METADATA.get(profile.pest_id, {})
        results.append({
            "pest_id": profile.pest_id,
            "common_name": profile.common_name,
            "scientific_name": profile.scientific_name,
            "image_url": profile.image_url,
            "fallback_image_url": image_meta.get("fallback"),
            "image_description": f"Field photograph associated with {profile.common_name}",
            "image_credit": image_meta.get("credit"),
            "image_source_url": image_meta.get("source_url"),
            "image_license": image_meta.get("license"),
            "outbreak_score": round(score, 1),
            "probability": round(probability, 5),
            "risk_class": _risk_class(score),
            "affected_part": profile.affected_part,
            "characteristic_signs": profile.characteristic_signs,
            "active_symptoms": symptom_details,
            "drivers": drivers,
            "ai_recommendations": recommendations,
            "formula": "score = 100 × logistic(prior log-odds + climate + tree vulnerability + farm-condition deficit + symptom evidence - management protection)",
            "calculation_terms": {
                "prior_probability": profile.prior,
                "climate_signal": round(climate_signal, 4),
                "vulnerability_signal": round(vulnerability_signal, 4),
                "farm_condition_deficit": round(condition_vulnerability, 4),
                "symptom_signal": round(symptom_signal, 4),
                "management_protection": round(protection, 4),
            },
        })

    results.sort(key=lambda item: item["outbreak_score"], reverse=True)
    overall = max((item["outbreak_score"] for item in results), default=0.0)
    weighted = sum(item["outbreak_score"] * weight for item, weight in zip(results, np.linspace(1.0, 0.45, len(results)))) / max(1e-9, sum(np.linspace(1.0, 0.45, len(results))))
    return {
        "overall_outbreak_pressure": round(float(weighted), 1),
        "highest_outbreak_score": round(float(overall), 1),
        "top_risk_pest": results[0]["common_name"] if results else None,
        "pests": results,
        "input_conditions": {
            "temperature_c": request.temperature_c,
            "humidity_percent": request.humidity_percent,
            "rainfall_mm_week": request.rainfall_mm_week,
            "wind_speed_kmh": request.wind_speed_kmh,
            "farm_condition_score": request.farm_condition_score,
        },
        "method": "Transparent pest-specific logistic scoring with environmental suitability, farm vulnerability, observed symptoms, and management protection.",
        "guidance_basis": [
            "Philippine Department of Agriculture Agricultural Training Institute coconut specialist guidance",
            "FAO integrated pest-management principles for coconut and palm pests",
            "Philippine Coconut Authority and local agriculture-office confirmation is recommended for severe cases",
        ],
        "limitations": [
            "Scores indicate inspection priority and outbreak plausibility; they are not laboratory identification.",
            "Risk coefficients are development parameters and require calibration with georeferenced field surveillance data.",
            "Only registered and locally approved control products should be considered with professional guidance.",
        ],
    }
