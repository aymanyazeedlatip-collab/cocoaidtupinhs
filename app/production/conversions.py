from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any

from app.data_foundation.repository import connection
from app.domain.enums import DataQualityFlag, ProductType
from app.domain.production import LegacyVarietyClass, ProductEstimate
from app.domain.units import UnitCode

MIN_VARIETY_FACTOR = 0.70
MAX_VARIETY_FACTOR = 1.30
VARIETY_PARAMETER_VERSION = "pca-variety-conversions-1.0.0"


def _class_value(value: LegacyVarietyClass) -> str | None:
    mapping = {
        LegacyVarietyClass.TALL: "tall",
        LegacyVarietyClass.DWARF: "dwarf",
        LegacyVarietyClass.HYBRID: "hybrid",
    }
    return mapping.get(value)


def load_variety_parameters(
    variety_id: str | None,
    variety_class: LegacyVarietyClass,
    *,
    database_path: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, float], list[str]]:
    warnings: list[str] = []
    with connection(database_path) as conn:
        variety = None
        if variety_id:
            row = conn.execute(
                """SELECT id, name, code, variety_class, confidence, source_document_id, source_page
                   FROM coconut_varieties WHERE id = ? OR lower(code) = lower(?) OR lower(name) = lower(?)""",
                (variety_id, variety_id, variety_id),
            ).fetchone()
            variety = dict(row) if row else None
            if not variety:
                warnings.append(f"Named variety '{variety_id}' was not found; no within-class adjustment was applied.")
        if variety is None:
            return None, {}, warnings
        params = {
            row["parameter_name"]: float(row["value"])
            for row in conn.execute(
                "SELECT parameter_name, value FROM variety_parameters WHERE variety_id = ?",
                (variety["id"],),
            ).fetchall()
        }
        return variety, params, warnings


def variety_adjustment_factor(
    variety: dict[str, Any] | None,
    params: dict[str, float],
    variety_class: LegacyVarietyClass,
    *,
    database_path: Path | None = None,
) -> tuple[float, str, list[str]]:
    warnings: list[str] = []
    if not variety or "nuts_per_hectare" not in params:
        return 1.0, "No named-variety yield adjustment was available.", warnings
    class_name = variety.get("variety_class") or _class_value(variety_class)
    with connection(database_path) as conn:
        rows = conn.execute(
            """SELECT p.value FROM variety_parameters p
               JOIN coconut_varieties v ON v.id = p.variety_id
               WHERE v.variety_class = ? AND p.parameter_name = 'nuts_per_hectare'""",
            (class_name,),
        ).fetchall()
    values = [float(row[0]) for row in rows]
    if not values or median(values) <= 0:
        return 1.0, "The selected variety class had no valid nuts-per-hectare reference median.", warnings
    raw_factor = params["nuts_per_hectare"] / median(values)
    factor = min(MAX_VARIETY_FACTOR, max(MIN_VARIETY_FACTOR, raw_factor))
    if factor != raw_factor:
        warnings.append(
            f"The raw named-variety factor {raw_factor:.3f} was capped to the validated range {MIN_VARIETY_FACTOR:.2f}-{MAX_VARIETY_FACTOR:.2f}."
        )
    basis = (
        f"Within-{class_name} adjustment using PCA nuts_per_hectare: selected={params['nuts_per_hectare']:.3f}, "
        f"class median={median(values):.3f}, applied factor={factor:.3f}."
    )
    return factor, basis, warnings


def build_product_estimates(
    annual_whole_fruit_tons: float,
    params: dict[str, float],
    *,
    young_nut_share: float,
) -> tuple[list[ProductEstimate], list[str]]:
    warnings: list[str] = []
    estimates = [ProductEstimate(
        product=ProductType.WHOLE_NUT_WITH_HUSK,
        quantity=annual_whole_fruit_tons,
        unit=UnitCode.TONNE,
        estimate_kind="direct_model_output",
        conversion_basis="Retained production model output interpreted as annual whole-fruit mass with husk.",
        quality_flags=[DataQualityFlag.REFERENCE_ONLY],
    )]
    fruit_weight_g = params.get("fruit_weight_g")
    if not fruit_weight_g or fruit_weight_g <= 0:
        warnings.append("Named-variety fruit weight is unavailable; nut counts and component conversions were omitted.")
        return estimates, warnings
    nut_count = annual_whole_fruit_tons * 1_000_000.0 / fruit_weight_g
    mature_count = nut_count * (1.0 - young_nut_share)
    young_count = nut_count * young_nut_share
    estimates.extend([
        ProductEstimate(
            product=ProductType.MATURE_NUT, quantity=mature_count, unit=UnitCode.COUNT,
            estimate_kind="official_share_split",
            conversion_basis=f"Whole-fruit mass divided by PCA fruit_weight_g, then multiplied by mature share {1-young_nut_share:.4f}.",
            parameter_names=["fruit_weight_g"], quality_flags=[DataQualityFlag.REFERENCE_ONLY],
        ),
        ProductEstimate(
            product=ProductType.YOUNG_NUT, quantity=young_count, unit=UnitCode.COUNT,
            estimate_kind="official_share_split",
            conversion_basis=f"Whole-fruit mass divided by PCA fruit_weight_g, then multiplied by young share {young_nut_share:.4f}.",
            parameter_names=["fruit_weight_g"], quality_flags=[DataQualityFlag.REFERENCE_ONLY],
        ),
    ])
    component_map = {
        "copra_per_nut_g": ProductType.COPRA,
        "husk_weight_g": ProductType.HUSK,
        "shell_weight_g": ProductType.SHELL,
        "meat_weight_g": ProductType.MEAT,
        "water_weight_g": ProductType.COCONUT_WATER,
    }
    for parameter, product in component_map.items():
        value = params.get(parameter)
        if value is None:
            continue
        estimates.append(ProductEstimate(
            product=product,
            quantity=mature_count * value / 1000.0,
            unit=UnitCode.KILOGRAM,
            estimate_kind="variety_conversion",
            conversion_basis=f"Estimated mature-nut count multiplied by PCA {parameter}; young-nut share is excluded from mature-fruit component conversion.",
            parameter_names=["fruit_weight_g", parameter],
            quality_flags=[DataQualityFlag.REFERENCE_ONLY],
        ))
    vco_ml = params.get("vco_per_nut_ml")
    if vco_ml is not None:
        # UnitCode has no litre code yet, so retain mass-equivalent kg only when a direct unit is supported.
        warnings.append("VCO potential exists for this PCA variety, but litre output is deferred until a canonical volume unit is added.")
    return estimates, warnings
