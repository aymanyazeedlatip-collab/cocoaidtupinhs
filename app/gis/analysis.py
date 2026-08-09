from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from app.math.bayes import evaluate_pest_risk
from app.math.suitability import suitability_index
from app.schemas.analysis import PestRiskRequest, SuitabilityRequest, RehabilitationPlanRequest
from app.schemas.farm import FarmCreate

EARTH_RADIUS_M = 6_371_000.0


def _local_xy(points: list[list[float]]) -> tuple[list[tuple[float, float]], float]:
    lat0 = math.radians(sum(point[0] for point in points) / len(points))
    xy = []
    for lat, lon in points:
        x = math.radians(lon) * EARTH_RADIUS_M * math.cos(lat0)
        y = math.radians(lat) * EARTH_RADIUS_M
        xy.append((x, y))
    return xy, lat0


def polygon_area_hectares(points: list[list[float]]) -> float:
    if len(points) < 3:
        return 0.0
    xy, _ = _local_xy(points)
    twice_area = 0.0
    for index, (x1, y1) in enumerate(xy):
        x2, y2 = xy[(index + 1) % len(xy)]
        twice_area += x1 * y2 - x2 * y1
    return abs(twice_area) / 2 / 10_000


def centroid(points: list[list[float]], fallback: tuple[float, float]) -> dict[str, float]:
    if len(points) < 3:
        return {"latitude": fallback[0], "longitude": fallback[1]}
    xy, lat0 = _local_xy(points)
    cross_sum = 0.0
    cx = 0.0
    cy = 0.0
    for index, (x1, y1) in enumerate(xy):
        x2, y2 = xy[(index + 1) % len(xy)]
        cross = x1 * y2 - x2 * y1
        cross_sum += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(cross_sum) < 1e-9:
        return {
            "latitude": sum(point[0] for point in points) / len(points),
            "longitude": sum(point[1] for point in points) / len(points),
        }
    cx /= 3 * cross_sum
    cy /= 3 * cross_sum
    return {
        "latitude": math.degrees(cy / EARTH_RADIUS_M),
        "longitude": math.degrees(cx / (EARTH_RADIUS_M * math.cos(lat0))),
    }


def _point_in_polygon(latitude: float, longitude: float, polygon: list[list[float]]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        crosses = ((yi > latitude) != (yj > latitude)) and (
            longitude < (xj - xi) * (latitude - yi) / (yj - yi) + xi
        )
        if crosses:
            inside = not inside
        j = i
    return inside


def farm_assessment(farm: FarmCreate) -> dict[str, Any]:
    tree_total = farm.trees.total_trees
    productive_recovering = (farm.trees.productive + farm.trees.recovering) / tree_total
    at_risk = (farm.trees.aging + farm.trees.stressed + farm.trees.infested + farm.trees.dead) / tree_total
    polygon_area = polygon_area_hectares(farm.location.polygon)
    data_quality_inputs = list(farm.provenance.values())
    confidence_map = {
        "measured": 1.0,
        "laboratory_test": 1.0,
        "government_record": 0.9,
        "farmer_reported": 0.75,
        "public_raster": 0.65,
        "public_statistic": 0.6,
        "estimated": 0.45,
        "synthetic_reference_based": 0.35,
        "missing": 0.0,
    }
    quality = np.mean([confidence_map.get(str(value), 0.4) for value in data_quality_inputs]) if data_quality_inputs else 0.35

    computed_yield = farm.production.annual_production_tons / farm.area_hectares
    yield_difference = abs(computed_yield - farm.production.yield_tons_per_hectare)
    yield_difference_fraction = yield_difference / max(computed_yield, 0.1)
    area_difference_fraction = (
        abs(polygon_area - farm.area_hectares) / farm.area_hectares if polygon_area > 0 else None
    )
    density = tree_total / farm.area_hectares
    warnings = ["Low provenance confidence widens uncertainty; it does not directly alter biological conditions."]
    if area_difference_fraction is not None and area_difference_fraction > 0.20:
        warnings.append("The drawn polygon area differs from the entered farm area by more than 20%; verify the boundary or area entry.")
    if yield_difference_fraction > 0.15:
        warnings.append("Annual production divided by farm area does not match the entered yield per hectare; verify both production fields.")
    if density < 20 or density > 400:
        warnings.append("The calculated tree density is unusually low or high for a coconut farm; verify tree counts and area.")

    return {
        "centroid": centroid(farm.location.polygon, (farm.location.latitude, farm.location.longitude)),
        "entered_area_hectares": farm.area_hectares,
        "polygon_area_hectares": round(polygon_area, 4) if polygon_area else None,
        "area_difference_percent": round(area_difference_fraction * 100, 2) if area_difference_fraction is not None else None,
        "tree_density_per_hectare": round(density, 2),
        "productive_recovering_fraction": round(productive_recovering, 4),
        "at_risk_fraction": round(at_risk, 4),
        "entered_yield_tons_per_hectare": farm.production.yield_tons_per_hectare,
        "calculated_yield_tons_per_hectare": round(computed_yield, 4),
        "yield_difference_percent": round(yield_difference_fraction * 100, 2),
        "data_quality_score": round(float(quality), 4),
        "data_quality_class": "High" if quality >= 0.8 else "Moderate" if quality >= 0.55 else "Low",
        "warnings": warnings,
    }


def rehabilitation_grid(farm: FarmCreate, rows: int = 5, cols: int = 5) -> dict[str, Any]:
    rows = max(2, min(rows, 10))
    cols = max(2, min(cols, 10))
    polygon = farm.location.polygon
    if polygon:
        lats = [point[0] for point in polygon]
        lons = [point[1] for point in polygon]
        south, north, west, east = min(lats), max(lats), min(lons), max(lons)
    else:
        # Use half the side length so the generated square approximates the
        # entered area rather than four times the entered area.
        delta_lat = max(0.0000001, math.sqrt(farm.area_hectares * 10_000) / (2 * EARTH_RADIUS_M))
        delta_lon = delta_lat / max(math.cos(math.radians(farm.location.latitude)), 0.2)
        south, north = farm.location.latitude - math.degrees(delta_lat), farm.location.latitude + math.degrees(delta_lat)
        west, east = farm.location.longitude - math.degrees(delta_lon), farm.location.longitude + math.degrees(delta_lon)

    pest = evaluate_pest_risk(PestRiskRequest(
        prior_probability=0.15,
        symptoms=farm.symptoms,
        humidity_percent=78,
        rainfall_mm_month=180,
        average_tree_age=farm.trees.average_age_years,
    ))["posterior_probability"]
    base_suit = suitability_index(SuitabilityRequest(soil_terrain=farm.soil_terrain))["score"]
    aging_risk = farm.trees.aging / farm.trees.total_trees
    decline_risk = (farm.trees.stressed + farm.trees.infested + farm.trees.dead) / farm.trees.total_trees
    terrain_score = float(np.clip(1 - farm.soil_terrain.slope_degrees / 40, 0, 1))
    soil_score = float(np.clip(base_suit, 0, 1))
    climate_score = 0.78
    recovery_potential = float(np.clip(0.45 * soil_score + 0.30 * climate_score + 0.25 * terrain_score, 0, 1))
    baseline_priority = float(np.clip(
        100 * (
            0.27 * aging_risk
            + 0.27 * pest
            + 0.24 * decline_risk
            + 0.17 * (1 - soil_score)
            + 0.05 * recovery_potential
        ),
        0,
        100,
    ))
    category = "Low" if baseline_priority < 30 else "Moderate" if baseline_priority < 55 else "High" if baseline_priority < 75 else "Critical"
    action = (
        "Maintain and monitor" if category == "Low" else
        "Targeted monitoring and soil support" if category == "Moderate" else
        "Prioritize rehabilitation assessment" if category == "High" else
        "Immediate combined rehabilitation assessment"
    )

    cells = []
    excluded_cells = 0
    for row in range(rows):
        for col in range(cols):
            lat1 = south + (north - south) * row / rows
            lat2 = south + (north - south) * (row + 1) / rows
            lon1 = west + (east - west) * col / cols
            lon2 = west + (east - west) * (col + 1) / cols
            center_lat = (lat1 + lat2) / 2
            center_lon = (lon1 + lon2) / 2
            if polygon and not _point_in_polygon(center_lat, center_lon, polygon):
                excluded_cells += 1
                continue
            cells.append({
                "id": f"R{row + 1}C{col + 1}",
                "bounds": [[lat1, lon1], [lat2, lon2]],
                "center": {"latitude": center_lat, "longitude": center_lon},
                "terrain_score": round(terrain_score, 4),
                "soil_score": round(soil_score, 4),
                "climate_score": round(climate_score, 4),
                "pest_risk": round(float(pest), 4),
                "tree_age_risk": round(aging_risk, 4),
                "productivity_decline_risk": round(decline_risk, 4),
                "recovery_potential": round(recovery_potential, 4),
                "priority": round(baseline_priority, 2),
                "class": category,
                "recommended_action": action,
                "spatial_evidence_status": "uniform_baseline",
                "explanation": (
                    "This cell uses the farm-wide baseline because no measured within-farm soil, terrain, tree-health, "
                    "or pest raster was supplied. COCO-AID does not invent local variation."
                ),
            })

    return {
        "rows": rows,
        "cols": cols,
        "bounds": {"south": south, "north": north, "west": west, "east": east},
        "cells": cells,
        "excluded_cells_outside_polygon": excluded_cells,
        "spatial_resolution_status": "uniform_baseline",
        "data_source_type": "synthetic_reference_based spatial baseline",
        "warning": (
            "All visible cells have the same farm-wide score because measured within-farm layers are unavailable. "
            "The grid indicates management zones only; it does not claim measured spatial differences."
        ),
    }

_REHAB_LABELS = {
    "typhoon": "Typhoon or damaging-wind exposure",
    "extreme_rain": "Extreme rainfall or waterlogging",
    "heavy_rain_forecast": "Heavy-rain forecast",
    "rain_forecast": "Rain forecast",
    "drought": "Extended drought",
    "heat_stress": "Heat stress",
    "other": "Weather-related farm stress",
}

_REHAB_PROCEDURES = {
    "typhoon": [
        "Enter only after local authorities and field conditions are safe; mark leaning, uprooted, snapped, and crown-damaged palms.",
        "Remove hanging or broken material that creates an immediate hazard, while avoiding unnecessary removal of healthy green fronds.",
        "Open blocked drains and access routes, record damaged palms by zone, and prioritize palms with exposed roots or severe crown loss.",
        "Inspect wounds and debris for rhinoceros beetle and other pest breeding sites; apply sanitation and monitoring before considering control products.",
        "Classify palms for recovery, support, or replacement, then recheck recovery and new-leaf emergence after 30 and 90 days.",
    ],
    "extreme_rain": [
        "Inspect drainage and standing-water areas as soon as access is safe; restore water movement before applying fertilizer.",
        "Check roots, spear leaves, crown tissues, and young palms for waterlogging, rot, yellowing, and lodging.",
        "Remove only irrecoverable or hazardous material and keep sanitation records for each affected zone.",
        "Delay fertilizer or soil amendments while soil is saturated; resume only after drainage and root-zone condition are verified.",
        "Reinspect after one and four weeks for delayed root decline, crown symptoms, and pest or disease activity.",
    ],
    "drought": [
        "Confirm moisture stress using soil condition, leaf folding, premature nut fall, and crown appearance rather than rainfall alone.",
        "Conserve moisture with clean organic mulch placed away from the trunk and prioritize water for young or recovering palms where feasible.",
        "Reduce competing weeds without disturbing major roots, and postpone high-salt fertilizer applications until adequate moisture returns.",
        "Inspect for mites, scale insects, and other pests favored by stressed palms, recording symptoms before treatment decisions.",
        "Reassess survival, flowering, and nut retention after rainfall resumes; replace palms only after recovery potential is evaluated.",
    ],
    "heat_stress": [
        "Inspect young, recently replanted, and exposed palms for scorching, spear damage, moisture deficit, and premature nut fall.",
        "Prioritize shade or temporary protection for vulnerable young palms and maintain mulch without covering the trunk base.",
        "Schedule irrigation or moisture-conservation work during cooler hours where water is available and locally permitted.",
        "Avoid major pruning or fertilizer applications during peak stress unless a local coconut specialist recommends them.",
        "Recheck crown growth and pest activity after temperatures moderate, documenting palms that fail to resume growth.",
    ],
    "other": [
        "Conduct a georeferenced field inspection and confirm damage before starting rehabilitation work.",
        "Separate immediate safety work from agronomic recovery work and document every affected management zone.",
        "Restore drainage, sanitation, and access first, then evaluate soil, roots, crowns, pests, and productive capacity.",
        "Use local agricultural-extension advice for replacement material, fertilizer, and registered pest-control decisions.",
        "Schedule follow-up inspections after 30 and 90 days to confirm recovery or replacement needs.",
    ],
}


def _rehab_event_kind(value: str) -> str:
    if value in {"heavy_rain_forecast", "rain_forecast"}:
        return "extreme_rain"
    return value if value in _REHAB_PROCEDURES else "other"


def _stable_event_seed(event_type: str, start_date: str, end_date: str) -> int:
    digest = hashlib.sha256(f"{event_type}|{start_date}|{end_date}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _grid_extent(farm: FarmCreate) -> tuple[list[list[float]], float, float, float, float]:
    polygon = farm.location.polygon
    if polygon:
        lats = [point[0] for point in polygon]
        lons = [point[1] for point in polygon]
        return polygon, min(lats), max(lats), min(lons), max(lons)
    delta_lat = max(0.0000001, math.sqrt(farm.area_hectares * 10_000) / (2 * EARTH_RADIUS_M))
    delta_lon = delta_lat / max(math.cos(math.radians(farm.location.latitude)), 0.2)
    south = farm.location.latitude - math.degrees(delta_lat)
    north = farm.location.latitude + math.degrees(delta_lat)
    west = farm.location.longitude - math.degrees(delta_lon)
    east = farm.location.longitude + math.degrees(delta_lon)
    polygon = [[south, west], [south, east], [north, east], [north, west]]
    return polygon, south, north, west, east


def _event_surface(kind: str, x: float, y: float, seed: int, farm: FarmCreate) -> float:
    rng = np.random.default_rng(seed)
    centers = [(float(rng.uniform(0.16, 0.84)), float(rng.uniform(0.16, 0.84)), float(rng.uniform(0.18, 0.34)))]
    if kind in {"typhoon", "extreme_rain"}:
        centers.append((float(rng.uniform(0.12, 0.88)), float(rng.uniform(0.12, 0.88)), float(rng.uniform(0.20, 0.38))))
    radial = 0.0
    for cx, cy, sigma in centers:
        radial = max(radial, math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sigma**2)))
    edge = min(1.0, 2.2 * max(abs(x - 0.5), abs(y - 0.5)))
    slope = float(np.clip(farm.soil_terrain.slope_degrees / 30.0, 0, 1))
    drainage_deficit = 1.0 - float(farm.soil_terrain.drainage_index)
    if kind == "typhoon":
        direction = float(rng.uniform(0, 2 * math.pi))
        exposed = float(np.clip(0.5 + 0.5 * ((x - 0.5) * math.cos(direction) + (y - 0.5) * math.sin(direction)) * 2.2, 0, 1))
        return float(np.clip(0.46 * radial + 0.30 * exposed + 0.16 * edge + 0.08 * slope, 0, 1))
    if kind == "extreme_rain":
        low_proxy = float(np.clip(1.1 - y + 0.15 * math.sin(2 * math.pi * x), 0, 1))
        return float(np.clip(0.45 * radial + 0.28 * low_proxy + 0.17 * drainage_deficit + 0.10 * (1 - slope), 0, 1))
    if kind == "drought":
        return float(np.clip(0.55 * edge + 0.25 * slope + 0.20 * radial, 0, 1))
    if kind == "heat_stress":
        return float(np.clip(0.44 * edge + 0.34 * radial + 0.22 * slope, 0, 1))
    return float(np.clip(0.65 * radial + 0.35 * edge, 0, 1))


def rehabilitation_event_plans(request: RehabilitationPlanRequest) -> dict[str, Any]:
    farm = request.farm
    polygon, south, north, west, east = _grid_extent(farm)
    rows, cols = request.rows, request.cols
    base_map = rehabilitation_grid(farm, rows=min(rows, 10), cols=min(cols, 10))
    base_priority = float(np.mean([cell["priority"] for cell in base_map["cells"]])) if base_map["cells"] else 25.0
    decline_fraction = (farm.trees.stressed + farm.trees.infested + farm.trees.dead) / max(1, farm.trees.total_trees)
    events = list(request.hazards)
    if not events:
        from app.schemas.analysis import RehabilitationHazardInput
        events = [RehabilitationHazardInput(
            event_type="other",
            label="Current farm-condition rehabilitation screening",
            start_date=datetime.now().date(),
            end_date=datetime.now().date(),
            peak_severity=float(np.clip(base_priority / 100, 0.15, 0.75)),
            estimated_production_loss_tons=0,
            loss_percent_of_event_baseline=0,
            estimated_trees_affected=int(round(farm.trees.total_trees * decline_fraction)),
            data_mode="current_farm_condition",
            confidence="Farm-wide screening",
        )]

    plans: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        kind = _rehab_event_kind(event.event_type)
        seed = _stable_event_seed(event.event_type, event.start_date.isoformat(), event.end_date.isoformat())
        severity = float(np.clip(event.peak_severity, 0, 1))
        loss_fraction = float(np.clip(event.loss_percent_of_event_baseline / 100, 0, 1))
        impact = float(np.clip(0.62 * severity + 0.38 * loss_fraction, 0, 1))
        if kind == "typhoon":
            impact = min(1.0, impact * 1.12)
        elif kind == "extreme_rain":
            impact = min(1.0, impact * (1.0 + 0.18 * (1 - farm.soil_terrain.drainage_index)))
        elif kind in {"drought", "heat_stress"}:
            impact = min(1.0, impact * (1.0 + 0.12 * farm.soil_terrain.slope_degrees / 20))

        cells: list[dict[str, Any]] = []
        counts = {"No Damage": 0, "Needs inspection": 0, "Needs Rehabilitation": 0}
        excluded = 0
        for row in range(rows):
            for col in range(cols):
                lat1 = south + (north - south) * row / rows
                lat2 = south + (north - south) * (row + 1) / rows
                lon1 = west + (east - west) * col / cols
                lon2 = west + (east - west) * (col + 1) / cols
                center_lat = (lat1 + lat2) / 2
                center_lon = (lon1 + lon2) / 2
                if polygon and not _point_in_polygon(center_lat, center_lon, polygon):
                    excluded += 1
                    continue
                x = (center_lon - west) / max(east - west, 1e-12)
                y = (center_lat - south) / max(north - south, 1e-12)
                surface = _event_surface(kind, x, y, seed, farm)
                vulnerability = float(np.clip(0.40 * base_priority / 100 + 0.35 * decline_fraction + 0.25 * (1 - farm.soil_terrain.drainage_index), 0, 1))
                # Use the square root of event impact so moderate but operationally
                # important events still produce inspection zones, while severe events
                # can generate concentrated rehabilitation zones. This avoids a
                # misleading all-green map for an event with documented loss.
                event_pressure = math.sqrt(max(0.0, impact))
                score = float(np.clip(100 * (
                    0.05 * vulnerability
                    + event_pressure * (0.08 + 0.92 * surface)
                    + 0.08 * loss_fraction
                ), 0, 100))
                if score < 28:
                    cls = "No Damage"
                    action = "No immediate damage action; continue scheduled monitoring."
                elif score < 55:
                    cls = "Needs inspection"
                    action = "Inspect this zone and verify crown, root, drainage, pest, and tree-stability conditions."
                else:
                    cls = "Needs Rehabilitation"
                    action = "Prioritize field verification and a documented rehabilitation work order for this zone."
                counts[cls] += 1
                cells.append({
                    "id": f"E{index + 1}-R{row + 1}C{col + 1}",
                    "bounds": [[lat1, lon1], [lat2, lon2]],
                    "center": {"latitude": center_lat, "longitude": center_lon},
                    "damage_score": round(score, 1),
                    "class": cls,
                    "recommended_action": action,
                    "event_type": event.event_type,
                    "surface_factor": round(surface, 4),
                    "impact_factor": round(impact, 4),
                    "explanation": (
                        f"Model-estimated {event.label.lower()} exposure combines event severity ({severity:.2f}), "
                        f"event-period loss ({loss_fraction:.2f}), farm vulnerability, drainage, slope, and a smooth event footprint. "
                        "Confirm every red or yellow zone by field inspection before taking action."
                    ),
                })

        assessment_date = event.end_date + timedelta(days=request.assessment_delay_days)
        rehabilitation_date = event.end_date + timedelta(days=request.rehabilitation_delay_days)
        procedures = list(_REHAB_PROCEDURES.get(kind, _REHAB_PROCEDURES["other"]))
        plans.append({
            "id": f"rehab-event-{index + 1}",
            "event_index": index,
            "event_type": event.event_type,
            "event_label": event.label or _REHAB_LABELS.get(event.event_type, _REHAB_LABELS["other"]),
            "event_start_date": event.start_date.isoformat(),
            "event_end_date": event.end_date.isoformat(),
            "recommended_assessment_date": assessment_date.isoformat(),
            "recommended_rehabilitation_date": rehabilitation_date.isoformat(),
            "follow_up_30_date": (rehabilitation_date + timedelta(days=30)).isoformat(),
            "follow_up_90_date": (rehabilitation_date + timedelta(days=90)).isoformat(),
            "peak_severity_percent": round(severity * 100, 1),
            "estimated_loss_tons": round(event.estimated_production_loss_tons, 3),
            "estimated_loss_percent": round(event.loss_percent_of_event_baseline, 1),
            "estimated_trees_affected": event.estimated_trees_affected,
            "data_mode": event.data_mode,
            "confidence": event.confidence,
            "impact_factor": round(impact, 4),
            "counts": counts,
            "cells": cells,
            "excluded_cells_outside_polygon": excluded,
            "procedure": procedures,
            "ai_prompt": (
                f"Create a concise, farm-specific rehabilitation work plan for {farm.name} after {event.label}. "
                f"The event runs {event.start_date.isoformat()} to {event.end_date.isoformat()}, peak severity is {severity * 100:.1f}%, "
                f"estimated event-period loss is {event.loss_percent_of_event_baseline:.1f}%, and the planned rehabilitation date is "
                f"{rehabilitation_date.isoformat()}. Prioritize safety, field verification, sanitation, drainage or moisture management, "
                "integrated pest management, recovery monitoring, and consultation with the local agriculture office. Do not give pesticide doses."
            ),
        })

    return {
        "plans": plans,
        "rows": rows,
        "cols": cols,
        "bounds": {"south": south, "north": north, "west": west, "east": east},
        "polygon": polygon,
        "legend": [
            {"class": "No Damage", "color": "#2f9e5b", "meaning": "No immediate damage action"},
            {"class": "Needs inspection", "color": "#f2c94c", "meaning": "Field inspection required"},
            {"class": "Needs Rehabilitation", "color": "#d94841", "meaning": "Rehabilitation likely after verification"},
        ],
        "method": "Event-conditioned smooth exposure surface with farm vulnerability modifiers",
        "data_source_type": "model_estimated_event_rehabilitation_plan",
        "warning": (
            "The event heatmaps are planning aids derived from forecast or simulated hazards and farm-wide inputs. "
            "They are not post-event remote-sensing damage maps. Field inspection is required before rehabilitation work."
        ),
        "research_basis": [
            "Philippine Agricultural Training Institute Coconut Specialist Course: farm layout, field inspection, corrective-action timelines, and good agricultural practices.",
            "FAO coconut-sector rehabilitation guidance: systematic replanting, quality planting material, diversification, and sustained extension support.",
        ],
    }
