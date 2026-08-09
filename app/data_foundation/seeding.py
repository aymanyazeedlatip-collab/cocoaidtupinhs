from __future__ import annotations

import hashlib
import json
import mimetypes
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.data_foundation.repository import connection

ROOT = Path(__file__).resolve().parents[2]
SOURCE_CATALOG = ROOT / "data" / "reference" / "source_documents.json"
REFERENCE_CATALOG = ROOT / "data" / "reference" / "phase2_catalog.json"
INTERCROP_INCOME_ASSESSMENT = ROOT / "data" / "reference" / "intercrop_income_assessment.json"
INTERCROP_REQUIREMENTS = ROOT / "data" / "reference" / "intercrop_requirement_profiles.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_reference_data(*, database_path: Path | None = None, verify_files: bool = True) -> dict[str, int]:
    source_catalog = _load(SOURCE_CATALOG)
    catalog = _load(REFERENCE_CATALOG)
    now = _now()
    counts = {
        "source_documents": 0,
        "coconut_varieties": 0,
        "variety_parameters": 0,
        "pest_profiles": 0,
        "pest_evidence_rules": 0,
        "pest_management_actions": 0,
        "intercrop_candidates": 0,
        "canopy_light_parameters": 0,
        "fertilization_scenarios": 0,
    }
    with connection(database_path) as conn:
        for item in source_catalog["documents"]:
            source_path = ROOT / item["relative_path"]
            if verify_files:
                if not source_path.exists():
                    raise FileNotFoundError(f"Required source is missing: {source_path}")
                actual = _sha256(source_path)
                if actual != item["sha256"]:
                    raise ValueError(f"Checksum mismatch for {item['relative_path']}")
            conn.execute(
                """INSERT INTO source_documents
                   (id, category, title, organization, relative_path, sha256, media_type, page_count,
                    publication_year, access_class, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET category=excluded.category, title=excluded.title,
                   organization=excluded.organization, relative_path=excluded.relative_path,
                   sha256=excluded.sha256, media_type=excluded.media_type, page_count=excluded.page_count,
                   publication_year=excluded.publication_year, access_class=excluded.access_class,
                   notes=excluded.notes, updated_at=excluded.updated_at""",
                (
                    item["id"], item["category"], item["title"], item["organization"], item["relative_path"],
                    item["sha256"], item.get("media_type") or mimetypes.guess_type(item["relative_path"])[0] or "application/octet-stream",
                    item.get("page_count"), item.get("publication_year"), item.get("access_class", "internal_reference"),
                    item.get("notes"), now, now,
                ),
            )
            counts["source_documents"] += 1

        for item in catalog["varieties"]:
            flowering = item.get("first_flowering_years") or [None, None]
            conn.execute(
                """INSERT INTO coconut_varieties
                   (id, name, code, variety_class, female_parent_code, male_parent_code,
                    first_flowering_min_years, first_flowering_max_years, confidence,
                    source_document_id, source_page, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, code=excluded.code,
                   variety_class=excluded.variety_class, female_parent_code=excluded.female_parent_code,
                   male_parent_code=excluded.male_parent_code,
                   first_flowering_min_years=excluded.first_flowering_min_years,
                   first_flowering_max_years=excluded.first_flowering_max_years,
                   confidence=excluded.confidence, source_document_id=excluded.source_document_id,
                   source_page=excluded.source_page, updated_at=excluded.updated_at""",
                (item["id"], item["name"], item["code"], item["variety_class"], item.get("female_parent_code"),
                 item.get("male_parent_code"), flowering[0], flowering[1], item["confidence"],
                 item["source_document_id"], item["source_page"], now, now),
            )
            counts["coconut_varieties"] += 1
            for parameter_name, param in item["parameters"].items():
                parameter_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cocoaid:variety:{item['id']}:{parameter_name}"))
                conn.execute(
                    """INSERT INTO variety_parameters
                       (id, variety_id, parameter_name, value, uncertainty, unit, verification_status,
                        source_document_id, source_page, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(variety_id, parameter_name) DO UPDATE SET value=excluded.value,
                       uncertainty=excluded.uncertainty, unit=excluded.unit,
                       verification_status=excluded.verification_status,
                       source_document_id=excluded.source_document_id, source_page=excluded.source_page,
                       notes=excluded.notes""",
                    (parameter_id, item["id"], parameter_name, param["value"], param.get("uncertainty"), param["unit"],
                     "verified_visual", item["source_document_id"], item["source_page"], param.get("notes")),
                )
                counts["variety_parameters"] += 1

        for item in catalog["pests"]:
            conn.execute(
                """INSERT INTO pest_profiles
                   (id, common_name, scientific_name, profile_type, confidence, source_document_id,
                    source_page, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET common_name=excluded.common_name,
                   scientific_name=excluded.scientific_name, profile_type=excluded.profile_type,
                   confidence=excluded.confidence, source_document_id=excluded.source_document_id,
                   source_page=excluded.source_page, notes=excluded.notes, updated_at=excluded.updated_at""",
                (item["id"], item["common_name"], item.get("scientific_name"), item["profile_type"], item["confidence"],
                 item["source_document_id"], item["source_page"], item.get("notes"), now, now),
            )
            counts["pest_profiles"] += 1
            for factor_code, direction, condition, likelihood_ratio, confidence, explanation in item.get("rules", []):
                rule_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cocoaid:pest-rule:{item['id']}:{factor_code}"))
                conn.execute(
                    """INSERT INTO pest_evidence_rules
                       (id, pest_id, factor_code, direction, condition_json, likelihood_ratio, confidence,
                        source_document_id, source_page, explanation)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(pest_id, factor_code) DO UPDATE SET direction=excluded.direction,
                       condition_json=excluded.condition_json, likelihood_ratio=excluded.likelihood_ratio,
                       confidence=excluded.confidence, source_document_id=excluded.source_document_id,
                       source_page=excluded.source_page, explanation=excluded.explanation""",
                    (rule_id, item["id"], factor_code, direction, json.dumps(condition, sort_keys=True), likelihood_ratio,
                     confidence, item["source_document_id"], item["source_page"], explanation),
                )
                counts["pest_evidence_rules"] += 1
            for index, action in enumerate(item.get("actions", []), start=1):
                action_type, timing, action_text = action[:3]
                safety_notes = action[3] if len(action) > 3 else None
                action_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cocoaid:pest-action:{item['id']}:{index}:{action_type}"))
                conn.execute(
                    """INSERT INTO pest_management_actions
                       (id, pest_id, action_type, timing, action_text, safety_notes, source_document_id, source_page)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET action_type=excluded.action_type, timing=excluded.timing,
                       action_text=excluded.action_text, safety_notes=excluded.safety_notes,
                       source_document_id=excluded.source_document_id, source_page=excluded.source_page""",
                    (action_id, item["id"], action_type, timing, action_text, safety_notes,
                     item["source_document_id"], item["source_page"]),
                )
                counts["pest_management_actions"] += 1

        for item in catalog["intercrop_candidates"]:
            conn.execute(
                """INSERT INTO intercrop_candidates
                   (id, common_name, scientific_name, light_group, min_light_fraction, max_light_fraction,
                    confidence, source_document_id, source_page, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET common_name=excluded.common_name,
                   scientific_name=excluded.scientific_name, light_group=excluded.light_group,
                   min_light_fraction=excluded.min_light_fraction, max_light_fraction=excluded.max_light_fraction,
                   confidence=excluded.confidence, source_document_id=excluded.source_document_id,
                   source_page=excluded.source_page, notes=excluded.notes, updated_at=excluded.updated_at""",
                (item["id"], item["common_name"], item.get("scientific_name"), item["light_group"],
                 item["min_light_fraction"], item["max_light_fraction"], item["confidence"],
                 item["source_document_id"], item["source_page"], item.get("notes"), now, now),
            )
            counts["intercrop_candidates"] += 1

        for item in catalog["canopy_light_parameters"]:
            conn.execute(
                """INSERT INTO canopy_light_parameters
                   (id, spacing_label, design, spacing_x_m, spacing_y_m, palms_per_hectare,
                    palm_age_years, transmitted_light_fraction, suitable_crop_groups, confidence,
                    source_document_id, source_page)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET spacing_label=excluded.spacing_label, design=excluded.design,
                   spacing_x_m=excluded.spacing_x_m, spacing_y_m=excluded.spacing_y_m,
                   palms_per_hectare=excluded.palms_per_hectare, palm_age_years=excluded.palm_age_years,
                   transmitted_light_fraction=excluded.transmitted_light_fraction,
                   suitable_crop_groups=excluded.suitable_crop_groups, confidence=excluded.confidence,
                   source_document_id=excluded.source_document_id, source_page=excluded.source_page""",
                (item["id"], item["spacing_label"], item["design"], item["spacing_x_m"], item["spacing_y_m"],
                 item["palms_per_hectare"], item["palm_age_years"], item["transmitted_light_fraction"],
                 item["suitable_crop_groups"], item["confidence"], item["source_document_id"], item["source_page"]),
            )
            counts["canopy_light_parameters"] += 1

        for item in catalog["fertilization_scenarios"]:
            conn.execute(
                """INSERT INTO fertilization_scenarios
                   (id, name, scenario_type, frequency_text, timing_text, requirements_json, confidence,
                    source_document_id, source_page, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, scenario_type=excluded.scenario_type,
                   frequency_text=excluded.frequency_text, timing_text=excluded.timing_text,
                   requirements_json=excluded.requirements_json, confidence=excluded.confidence,
                   source_document_id=excluded.source_document_id, source_page=excluded.source_page,
                   notes=excluded.notes, updated_at=excluded.updated_at""",
                (item["id"], item["name"], item["scenario_type"], item.get("frequency_text"), item.get("timing_text"),
                 json.dumps(item["requirements"], sort_keys=True), item["confidence"], item["source_document_id"],
                 item["source_page"], item.get("notes"), now, now),
            )
            counts["fertilization_scenarios"] += 1

        has_requirement_profiles = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='intercrop_requirement_profiles'"
        ).fetchone() is not None
        if has_requirement_profiles and INTERCROP_REQUIREMENTS.exists():
            requirement_catalog = _load(INTERCROP_REQUIREMENTS)
            counts["intercrop_requirement_profiles"] = 0
            for item in requirement_catalog.get("profiles", []):
                conn.execute(
                    """INSERT INTO intercrop_requirement_profiles(
                           candidate_id, profile_version, min_temperature_c, max_temperature_c,
                           min_rainfall_mm_year, max_rainfall_mm_year, min_soil_ph, max_soil_ph,
                           min_soil_moisture_index, max_soil_moisture_index, min_drainage_index,
                           water_demand, root_competition, space_demand, nutrient_demand,
                           management_demand, pest_conflict_ids_json, beneficial_pest_ids_json,
                           economic_profile_crop, planting_months_json, harvest_months_json,
                           confidence, basis, notes, created_at, updated_at
                       ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(candidate_id) DO UPDATE SET
                           profile_version=excluded.profile_version,
                           min_temperature_c=excluded.min_temperature_c,
                           max_temperature_c=excluded.max_temperature_c,
                           min_rainfall_mm_year=excluded.min_rainfall_mm_year,
                           max_rainfall_mm_year=excluded.max_rainfall_mm_year,
                           min_soil_ph=excluded.min_soil_ph,
                           max_soil_ph=excluded.max_soil_ph,
                           min_soil_moisture_index=excluded.min_soil_moisture_index,
                           max_soil_moisture_index=excluded.max_soil_moisture_index,
                           min_drainage_index=excluded.min_drainage_index,
                           water_demand=excluded.water_demand,
                           root_competition=excluded.root_competition,
                           space_demand=excluded.space_demand,
                           nutrient_demand=excluded.nutrient_demand,
                           management_demand=excluded.management_demand,
                           pest_conflict_ids_json=excluded.pest_conflict_ids_json,
                           beneficial_pest_ids_json=excluded.beneficial_pest_ids_json,
                           economic_profile_crop=excluded.economic_profile_crop,
                           planting_months_json=excluded.planting_months_json,
                           harvest_months_json=excluded.harvest_months_json,
                           confidence=excluded.confidence, basis=excluded.basis,
                           notes=excluded.notes, updated_at=excluded.updated_at""",
                    (
                        item["candidate_id"], requirement_catalog["profile_version"],
                        item["min_temperature_c"], item["max_temperature_c"],
                        item["min_rainfall_mm_year"], item["max_rainfall_mm_year"],
                        item["min_soil_ph"], item["max_soil_ph"],
                        item["min_soil_moisture_index"], item["max_soil_moisture_index"],
                        item["min_drainage_index"], item["water_demand"],
                        item["root_competition"], item["space_demand"],
                        item["nutrient_demand"], item["management_demand"],
                        json.dumps(item.get("pest_conflict_ids", []), sort_keys=True),
                        json.dumps(item.get("beneficial_pest_ids", []), sort_keys=True),
                        item.get("economic_profile_crop"),
                        json.dumps(item.get("planting_months", []), sort_keys=True),
                        json.dumps(item.get("harvest_months", []), sort_keys=True),
                        item["confidence"], item["basis"], item["notes"], now, now,
                    ),
                )
                counts["intercrop_requirement_profiles"] += 1
            conn.execute(
                """INSERT INTO system_metadata(key, value, updated_at)
                   VALUES ('intercrop_requirement_profile_version', ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (requirement_catalog["profile_version"], now),
            )

        has_economic_profiles = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='intercrop_economic_profiles'"
        ).fetchone() is not None
        if has_economic_profiles and INTERCROP_INCOME_ASSESSMENT.exists():
            assessment = _load(INTERCROP_INCOME_ASSESSMENT)
            counts["intercrop_economic_profiles"] = 0
            for item in assessment.get("site_profiles", []):
                profile_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"cocoaid:intercrop-economic:{assessment['assessment_version']}:{item['site_code']}:{item['crop']}"
                ))
                quality_flags = [
                    "restricted_row_level_source",
                    "gross_revenue_not_net_profit",
                    "requires_inflation_and_market_normalization",
                ]
                conn.execute(
                    """INSERT INTO intercrop_economic_profiles(
                           id, source_document_id, assessment_version, site_code, crop, record_count,
                           area_stats_json, seedling_stats_json, unit_price_stats_json,
                           gross_income_year_stats_json, gross_income_per_hectare_stats_json,
                           reported_cost_stats_json, frequency_labels_json, quality_flags_json,
                           created_at, updated_at
                       ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(assessment_version, site_code, crop) DO UPDATE SET
                           record_count=excluded.record_count, area_stats_json=excluded.area_stats_json,
                           seedling_stats_json=excluded.seedling_stats_json,
                           unit_price_stats_json=excluded.unit_price_stats_json,
                           gross_income_year_stats_json=excluded.gross_income_year_stats_json,
                           gross_income_per_hectare_stats_json=excluded.gross_income_per_hectare_stats_json,
                           reported_cost_stats_json=excluded.reported_cost_stats_json,
                           frequency_labels_json=excluded.frequency_labels_json,
                           quality_flags_json=excluded.quality_flags_json, updated_at=excluded.updated_at""",
                    (
                        profile_id, "pca-intercrop-income-assessment-2024", assessment["assessment_version"],
                        item["site_code"], item["crop"], item["record_count"],
                        json.dumps(item["area_hectares"], sort_keys=True),
                        json.dumps(item["seedlings_qty"], sort_keys=True),
                        json.dumps(item["unit_price_php"], sort_keys=True),
                        json.dumps(item["gross_income_year_php"], sort_keys=True),
                        json.dumps(item["gross_income_per_hectare_php"], sort_keys=True),
                        json.dumps(item["reported_cost_total_php"], sort_keys=True),
                        json.dumps(item["frequency_labels"], sort_keys=True),
                        json.dumps(quality_flags, sort_keys=True), now, now,
                    ),
                )
                counts["intercrop_economic_profiles"] += 1

        conn.execute(
            """INSERT INTO system_metadata(key, value, updated_at) VALUES ('phase2_catalog_version', ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (catalog["catalog_version"], now),
        )
        if has_economic_profiles:
            conn.execute(
                """INSERT INTO system_metadata(key, value, updated_at) VALUES ('intercrop_income_assessment_version', ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                ((_load(INTERCROP_INCOME_ASSESSMENT).get("assessment_version") if INTERCROP_INCOME_ASSESSMENT.exists() else "missing"), now),
            )
    return counts
