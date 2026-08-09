from __future__ import annotations

from app.schemas.analysis import SuitabilityRequest


def trapezoid_membership(value: float, low: float, ideal_low: float, ideal_high: float, high: float) -> float:
    if not low <= ideal_low <= ideal_high <= high:
        raise ValueError("membership bounds must be ordered")
    if value <= low or value >= high:
        return 0.0
    if ideal_low <= value <= ideal_high:
        return 1.0
    if value < ideal_low:
        return (value - low) / max(ideal_low - low, 1e-9)
    return (high - value) / max(high - ideal_high, 1e-9)


WEIGHTS = {
    "rainfall": 0.18,
    "temperature": 0.15,
    "humidity": 0.08,
    "ph": 0.14,
    "nutrients": 0.14,
    "elevation": 0.08,
    "slope": 0.08,
    "drainage": 0.08,
    "drought": 0.04,
    "climate_stress": 0.03,
}


def suitability_index(request: SuitabilityRequest, ml_score: float | None = None) -> dict:
    st = request.soil_terrain
    scores = {
        "rainfall": trapezoid_membership(request.annual_rainfall_mm, 900, 1500, 2800, 4200),
        "temperature": trapezoid_membership(request.mean_temperature_c, 18, 24, 29, 36),
        "humidity": trapezoid_membership(request.humidity_percent, 45, 65, 88, 100),
        "ph": trapezoid_membership(st.soil_ph, 4.0, 5.5, 7.2, 8.6),
        "nutrients": (st.nitrogen_index + st.phosphorus_index + st.potassium_index) / 3,
        "elevation": trapezoid_membership(st.elevation_m, -50, 0, 600, 1400),
        "slope": trapezoid_membership(st.slope_degrees, 0, 0, 12, 35),
        "drainage": st.drainage_index,
        "drought": 1 - request.drought_exposure,
        "climate_stress": 1 - request.climate_stress,
    }
    baseline = sum(WEIGHTS[k] * scores[k] for k in WEIGHTS)
    if ml_score is not None:
        ml_score = min(1, max(0, ml_score))
        final = 0.7 * baseline + 0.3 * ml_score
        method = "Transparent agronomic index blended with synthetic-development ML regressor"
    else:
        final = baseline
        method = "Transparent agronomic suitability index"

    percent = round(final * 100, 2)
    category = "Unsuitable" if percent < 30 else "Marginal" if percent < 50 else "Moderately Suitable" if percent < 70 else "Suitable" if percent < 85 else "Highly Suitable"
    limiting = sorted(scores.items(), key=lambda item: item[1])[:3]
    return {
        "score": round(final, 6),
        "percentage": percent,
        "class": category,
        "component_scores": {k: round(v, 4) for k, v in scores.items()},
        "weights": WEIGHTS,
        "limiting_factors": [{"factor": k, "score": round(v, 4)} for k, v in limiting],
        "method": method,
        "warning": "Estimated public-layer values should be replaced by farm laboratory measurements when available.",
    }
