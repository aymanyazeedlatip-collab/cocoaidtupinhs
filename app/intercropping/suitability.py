from __future__ import annotations

import math
from calendar import monthrange
from datetime import date
from statistics import fmean
from typing import Any

from app.domain.enums import ConfidenceLevel
from app.domain.intercropping import (
    CanopyLightEstimate,
    IntercropCellContext,
    IntercropEconomicPotential,
    SuitabilityComponent,
)
from app.intercropping.parameters import PARAMETERS


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def range_score(value: float, minimum: float, maximum: float, *, tolerance_fraction: float = 0.30) -> float:
    """Plateau inside the target range with linear decay outside it."""
    if minimum <= value <= maximum:
        return 1.0
    span = max(maximum - minimum, abs(minimum) * 0.25, 0.1)
    tolerance = max(span * tolerance_fraction, 0.05)
    if value < minimum:
        return _clamp(1.0 - (minimum - value) / tolerance)
    return _clamp(1.0 - (value - maximum) / tolerance)


def threshold_score(value: float, minimum: float) -> float:
    if minimum <= 0:
        return 1.0
    return _clamp(value / minimum)


def inverse_demand_score(available: float, demand: float) -> float:
    demand = _clamp(demand)
    if demand <= 0.05:
        return 1.0
    return _clamp(available / demand)


def estimate_canopy_light(
    *,
    cell: IntercropCellContext,
    canopy_rows: list[dict[str, Any]],
    solar_radiation_mj_m2_day: float | None,
) -> CanopyLightEstimate:
    same_design = [row for row in canopy_rows if row["design"] == cell.canopy_design]
    candidates = same_design or canopy_rows
    if not candidates:
        raise ValueError("Canopy-light reference table is empty")

    # Select the spacing configuration nearest to the supplied geometry, then
    # interpolate the source-backed 20- and 40-year values by palm age.
    spacing_groups: dict[tuple[float, float, str], list[dict[str, Any]]] = {}
    for row in candidates:
        key = (float(row["spacing_x_m"]), float(row["spacing_y_m"]), row["design"])
        spacing_groups.setdefault(key, []).append(row)
    key = min(
        spacing_groups,
        key=lambda item: math.hypot(item[0] - cell.spacing_x_m, item[1] - cell.spacing_y_m),
    )
    rows = sorted(spacing_groups[key], key=lambda row: int(row["palm_age_years"]))
    if len(rows) == 1:
        base = float(rows[0]["transmitted_light_fraction"])
        source_ids = [rows[0]["id"]]
        method = "nearest spacing/design; single age reference"
        age_adjusted = False
    else:
        lower, upper = rows[0], rows[-1]
        low_age, high_age = float(lower["palm_age_years"]), float(upper["palm_age_years"])
        ratio = _clamp((cell.palm_age_years - low_age) / max(high_age - low_age, 1.0))
        base = float(lower["transmitted_light_fraction"]) + ratio * (
            float(upper["transmitted_light_fraction"]) - float(lower["transmitted_light_fraction"])
        )
        source_ids = [lower["id"], upper["id"]]
        method = "nearest spacing/design with bounded linear interpolation between PCA 20- and 40-year rows"
        age_adjusted = low_age < cell.palm_age_years < high_age

    density_factor = 1.0 + (
        PARAMETERS["canopy_density_reference"] - cell.canopy_density_index
    ) * PARAMETERS["canopy_density_adjustment_strength"]
    density_factor = max(
        PARAMETERS["canopy_density_factor_min"],
        min(PARAMETERS["canopy_density_factor_max"], density_factor),
    )
    if cell.row_orientation_degrees is None:
        orientation_factor = 1.0
    else:
        # Small, explicitly bounded engineering adjustment. It must not overpower
        # source-table transmission values.
        radians = math.radians(cell.row_orientation_degrees % 180)
        orientation_factor = 1.0 + PARAMETERS["orientation_adjustment_amplitude"] * math.cos(2 * radians)
    transmitted = _clamp(base * density_factor * orientation_factor)
    understory = None if solar_radiation_mj_m2_day is None else max(0.0, solar_radiation_mj_m2_day * transmitted)
    confidence = ConfidenceLevel.HIGH if len(source_ids) == 2 and same_design else ConfidenceLevel.MODERATE
    return CanopyLightEstimate(
        transmitted_light_fraction=transmitted,
        source_parameter_ids=source_ids,
        interpolation_method=method,
        age_adjusted=age_adjusted,
        density_adjustment_factor=density_factor,
        orientation_adjustment_factor=orientation_factor,
        understory_solar_radiation_mj_m2_day=understory,
        confidence=confidence,
    )


def component(
    factor: str,
    score: float,
    weight: float,
    explanation: str,
    *,
    hard_constraint_passed: bool = True,
) -> SuitabilityComponent:
    return SuitabilityComponent(
        factor=factor,
        score=_clamp(score),
        weight=weight,
        hard_constraint_passed=hard_constraint_passed,
        explanation=explanation,
    )


def geometric_score(components: list[SuitabilityComponent]) -> float:
    total_weight = sum(item.weight for item in components)
    if total_weight <= 0:
        return 0.0
    # A small floor keeps a single zero from making all diagnostics numerically opaque.
    log_sum = sum(item.weight * math.log(max(item.score, 1e-6)) for item in components)
    return math.exp(log_sum / total_weight)


def suitability_class(score: float) -> str:
    if score < 25:
        return "unsuitable"
    if score < 50:
        return "low"
    if score < PARAMETERS["high_score_threshold"]:
        return "moderate"
    if score < PARAMETERS["very_high_score_threshold"]:
        return "high"
    return "very_high"


def planting_window(assessed_on: date, months: list[int]) -> tuple[date | None, date | None]:
    valid = sorted({month for month in months if 1 <= month <= 12})
    if not valid:
        return None, None
    for year_offset in (0, 1):
        year = assessed_on.year + year_offset
        for month in valid:
            start = date(year, month, 1)
            if start >= assessed_on:
                return start, date(year, month, monthrange(year, month)[1])
    return None, None


def economic_potential(
    *,
    candidate_id: str,
    area_hectares: float,
    suitability_score_value: float,
    crop_profiles: dict[str, Any],
    enabled: bool,
) -> IntercropEconomicPotential:
    profile = crop_profiles.get(candidate_id)
    if not enabled or not profile:
        return IntercropEconomicPotential(
            status="not_available",
            basis=(
                "No sanitized empirical gross-revenue profile is available for this candidate. "
                "Phase 7 does not invent market values."
            ),
            quality_flags=["economic_profile_missing"],
        )
    stats = profile["gross_income_per_hectare_php"]
    scaling = max(PARAMETERS["economic_suitability_floor"], suitability_score_value / 100.0)
    return IntercropEconomicPotential(
        status="available",
        gross_revenue_lower_php=float(stats["p25"]) * area_hectares * scaling,
        gross_revenue_median_php=float(stats["median"]) * area_hectares * scaling,
        gross_revenue_upper_php=float(stats["p75"]) * area_hectares * scaling,
        basis=(
            "Sanitized historical gross revenue per hectare from the uploaded PCA Region XII income assessment, "
            "scaled by cell area and biophysical suitability. This is not net profit, ROI, or a guaranteed future price."
        ),
        quality_flags=[
            "gross_revenue_not_net_profit",
            "historical_price_not_inflation_adjusted",
            "restricted_row_level_source_aggregated",
            "suitability_scaled_scenario",
        ],
    )


def mean_feature(features: dict[str, float], name: str, default: float) -> float:
    value = features.get(name)
    return default if value is None else float(value)


def annualized_rainfall(features: dict[str, float]) -> float:
    rain90 = mean_feature(features, "rainfall_90d_mm", 0.0)
    return max(0.0, rain90 * 365.25 / 90.0)


def weather_temperature_estimate(features: dict[str, float]) -> float:
    # Phase 3 feature contract does not retain mean temperature. Infer a bounded
    # stress-adjusted development estimate and mark it as an assumption in output.
    heat_days = mean_feature(features, "heat_stress_days_30d", 0.0)
    return 27.0 + min(4.0, heat_days / 10.0)


def aggregate_crop_profiles(assessment: dict[str, Any]) -> dict[str, Any]:
    return dict(assessment.get("crop_profiles", {}))


def average_probability(values: list[float]) -> float:
    return fmean(values) if values else 0.0
