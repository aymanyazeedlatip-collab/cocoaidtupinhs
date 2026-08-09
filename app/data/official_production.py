from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import ROOT_DIR

PROFILE_PATH = ROOT_DIR / "data" / "official" / "psa_province_profiles.json"
ANNUAL_PATH = ROOT_DIR / "data" / "official" / "psa_coconut_production_annual.csv"

PRODUCT_LABELS = {
    "coconut_w_husk": "Coconut (w/ husk)",
    "coconut_mature": "Coconut Mature",
    "coconut_young": "Coconut Young",
}


def normalize_location(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\bprovince of\b", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


@lru_cache(maxsize=1)
def _dataset() -> dict[str, Any]:
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(f"Official production profile file is missing: {PROFILE_PATH}")
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def metadata() -> dict[str, Any]:
    return dict(_dataset()["metadata"])


def province_names() -> list[dict[str, str]]:
    result = []
    for profile in _dataset()["profiles"].values():
        result.append({"province": profile["province"], "region": profile.get("region") or ""})
    return sorted(result, key=lambda item: item["province"])


def province_profile(province: str | None, region: str | None = None) -> dict[str, Any]:
    data = _dataset()
    key = normalize_location(province)
    profile = data["profiles"].get(key)
    if profile:
        return profile

    # Conservative alias matching handles common labels such as “Davao del Sur Province”.
    if key:
        for candidate_key, candidate in data["profiles"].items():
            if key == candidate_key or key in candidate_key or candidate_key in key:
                return candidate

    region_key = normalize_location(region)
    if region_key:
        regional = data.get("regional_profiles", {}).get(region_key)
        if regional:
            return {
                "province": province or "Regional reference",
                "region": regional.get("location") or region or "",
                "normalized_name": key,
                "products": regional.get("products", {}),
                "mature_share_2025": 0.97,
                "young_share_2025": 0.03,
                "reference_level": "region",
            }

    national = data.get("regional_profiles", {}).get("philippines")
    return {
        "province": province or "National reference",
        "region": region or "Philippines",
        "normalized_name": key,
        "products": national.get("products", {}) if national else {},
        "mature_share_2025": 0.97,
        "young_share_2025": 0.03,
        "reference_level": "national",
    }


def _annual_history(product_data: dict[str, Any]) -> list[dict[str, Any]]:
    history = product_data.get("history", [])
    return [
        {
            "year": int(row["year"]),
            "annual_tons": float(row.get("annual_tons", 0.0)),
            "status": row.get("status", "official_psa"),
        }
        for row in history
    ]


def public_profile(province: str | None, region: str | None = None) -> dict[str, Any]:
    profile = province_profile(province, region)
    products: dict[str, Any] = {}
    for product, label in PRODUCT_LABELS.items():
        data = profile.get("products", {}).get(product, {})
        products[product] = {
            "label": label,
            "history": _annual_history(data),
            "latest_official_2025_tons": float(data.get("latest_official_2025_tons", 0.0)),
            "estimated_2026_tons": float(data.get("estimated_2026_tons", 0.0)),
            "quarter_shares": data.get("quarter_shares", {"q1": .25, "q2": .25, "q3": .25, "q4": .25}),
            "cagr_2015_2025": float(data.get("cagr_2015_2025", 0.0)),
        }
    return {
        "province": profile.get("province") or province,
        "region": profile.get("region") or region,
        "reference_level": profile.get("reference_level", "province"),
        "mature_share_2025": float(profile.get("mature_share_2025", .97)),
        "young_share_2025": float(profile.get("young_share_2025", .03)),
        "products": products,
        "metadata": metadata(),
    }


def production_calibration(province: str | None, region: str | None = None) -> dict[str, Any]:
    profile = public_profile(province, region)
    husk = profile["products"]["coconut_w_husk"]
    mature = profile["products"]["coconut_mature"]
    young = profile["products"]["coconut_young"]
    mature_share = float(profile.get("mature_share_2025", .97))
    young_share = float(profile.get("young_share_2025", .03))
    share_total = mature_share + young_share
    if share_total <= 0:
        mature_share, young_share = .97, .03
    else:
        mature_share /= share_total
        young_share /= share_total
    return {
        "province": profile["province"],
        "region": profile["region"],
        "reference_level": profile["reference_level"],
        "mature_share": mature_share,
        "young_share": young_share,
        "quarter_shares": {
            "coconut_w_husk": husk.get("quarter_shares") or {"q1": .25, "q2": .25, "q3": .25, "q4": .25},
            "coconut_mature": mature.get("quarter_shares") or {"q1": .25, "q2": .25, "q3": .25, "q4": .25},
            "coconut_young": young.get("quarter_shares") or {"q1": .25, "q2": .25, "q3": .25, "q4": .25},
        },
        "official_history": {
            "coconut_w_husk": husk["history"],
            "coconut_mature": mature["history"],
            "coconut_young": young["history"],
        },
        "latest_official_2025_tons": {
            "coconut_w_husk": husk["latest_official_2025_tons"],
            "coconut_mature": mature["latest_official_2025_tons"],
            "coconut_young": young["latest_official_2025_tons"],
        },
        "estimated_2026_tons": {
            "coconut_w_husk": husk["estimated_2026_tons"],
            "coconut_mature": mature["estimated_2026_tons"],
            "coconut_young": young["estimated_2026_tons"],
        },
        "trend_cagr": float(husk.get("cagr_2015_2025", 0.0)),
        "source": metadata(),
    }
