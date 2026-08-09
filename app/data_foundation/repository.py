from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.core.config import settings


@contextmanager
def connection(database_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(database_path or settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _rows(query: str, params: tuple[Any, ...] = (), *, database_path: Path | None = None) -> list[dict[str, Any]]:
    with connection(database_path) as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    tables = {
        "source_documents": "source_documents",
        "coconut_varieties": "coconut_varieties",
        "variety_parameters": "variety_parameters",
        "pest_profiles": "pest_profiles",
        "pest_evidence_rules": "pest_evidence_rules",
        "pest_management_actions": "pest_management_actions",
        "intercrop_candidates": "intercrop_candidates",
        "canopy_light_parameters": "canopy_light_parameters",
        "fertilization_scenarios": "fertilization_scenarios",
        "farmer_import_runs": "farmer_import_runs",
        "farmer_registry_records": "farmer_registry",
        "farmer_quality_flags": "farmer_quality_flags",
    }
    with connection(database_path) as conn:
        result: dict[str, int] = {}
        for key, table in tables.items():
            result[key] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        result["protected_farmer_identities"] = int(conn.execute("SELECT COUNT(*) FROM farmer_identities").fetchone()[0])
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intercrop_economic_profiles'").fetchone():
            result["intercrop_economic_profiles"] = int(conn.execute("SELECT COUNT(*) FROM intercrop_economic_profiles").fetchone()[0])
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intercrop_requirement_profiles'").fetchone():
            result["intercrop_requirement_profiles"] = int(conn.execute("SELECT COUNT(*) FROM intercrop_requirement_profiles").fetchone()[0])
        return result


def list_source_documents(*, include_restricted: bool = False, database_path: Path | None = None) -> list[dict[str, Any]]:
    clause = "" if include_restricted else "WHERE access_class <> 'restricted_pii'"
    return _rows(
        f"""SELECT id, category, title, organization, sha256, media_type, page_count,
                   publication_year, access_class, notes, created_at, updated_at
            FROM source_documents {clause} ORDER BY category, title""",
        database_path=database_path,
    )


def list_varieties(variety_class: str | None = None, *, database_path: Path | None = None) -> list[dict[str, Any]]:
    params: tuple[Any, ...] = ()
    where = ""
    if variety_class:
        where = "WHERE v.variety_class = ?"
        params = (variety_class,)
    rows = _rows(
        f"""SELECT v.*, d.title AS source_title
            FROM coconut_varieties v
            JOIN source_documents d ON d.id = v.source_document_id
            {where}
            ORDER BY v.variety_class, v.name""",
        params,
        database_path=database_path,
    )
    with connection(database_path) as conn:
        for row in rows:
            params_rows = conn.execute(
                """SELECT parameter_name, value, uncertainty, unit, verification_status, source_page, notes
                   FROM variety_parameters WHERE variety_id = ? ORDER BY parameter_name""",
                (row["id"],),
            ).fetchall()
            row["parameters"] = [dict(item) for item in params_rows]
    return rows


def list_pests(*, database_path: Path | None = None) -> list[dict[str, Any]]:
    rows = _rows(
        """SELECT p.*, d.title AS source_title FROM pest_profiles p
           JOIN source_documents d ON d.id = p.source_document_id ORDER BY p.common_name""",
        database_path=database_path,
    )
    with connection(database_path) as conn:
        for row in rows:
            rules = conn.execute(
                """SELECT factor_code, direction, condition_json, likelihood_ratio, confidence,
                          source_page, explanation
                   FROM pest_evidence_rules WHERE pest_id = ? ORDER BY factor_code""",
                (row["id"],),
            ).fetchall()
            actions = conn.execute(
                """SELECT action_type, timing, action_text, safety_notes, source_page
                   FROM pest_management_actions WHERE pest_id = ? ORDER BY action_type, id""",
                (row["id"],),
            ).fetchall()
            row["evidence_rules"] = [
                {**dict(item), "condition": json.loads(item["condition_json"])} for item in rules
            ]
            for item in row["evidence_rules"]:
                item.pop("condition_json", None)
            row["management_actions"] = [dict(item) for item in actions]
    return rows


def list_intercrops(*, database_path: Path | None = None) -> list[dict[str, Any]]:
    return _rows(
        """SELECT c.*, d.title AS source_title FROM intercrop_candidates c
           JOIN source_documents d ON d.id = c.source_document_id ORDER BY c.light_group, c.common_name""",
        database_path=database_path,
    )


def list_canopy_light_parameters(*, age_years: int | None = None, database_path: Path | None = None) -> list[dict[str, Any]]:
    where = "WHERE c.palm_age_years = ?" if age_years is not None else ""
    params: tuple[Any, ...] = (age_years,) if age_years is not None else ()
    return _rows(
        f"""SELECT c.*, d.title AS source_title FROM canopy_light_parameters c
            JOIN source_documents d ON d.id = c.source_document_id
            {where} ORDER BY c.spacing_x_m, c.spacing_y_m, c.design, c.palm_age_years""",
        params,
        database_path=database_path,
    )


def list_fertilization_scenarios(*, database_path: Path | None = None) -> list[dict[str, Any]]:
    rows = _rows(
        """SELECT f.*, d.title AS source_title FROM fertilization_scenarios f
           JOIN source_documents d ON d.id = f.source_document_id ORDER BY f.name""",
        database_path=database_path,
    )
    for row in rows:
        row["requirements"] = json.loads(row.pop("requirements_json"))
    return rows


def list_farmer_import_runs(*, database_path: Path | None = None) -> list[dict[str, Any]]:
    rows = _rows(
        """SELECT id, source_sha256, started_at, completed_at, status, sheet_count, total_rows,
                  accepted_rows, flagged_rows, duplicate_groups, error_count, summary_json
           FROM farmer_import_runs ORDER BY started_at DESC""",
        database_path=database_path,
    )
    for row in rows:
        row["summary"] = json.loads(row.pop("summary_json"))
    return rows


def farmer_registry_summary(*, database_path: Path | None = None) -> dict[str, Any]:
    with connection(database_path) as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM farmer_registry").fetchone()[0])
        by_status = {row[0]: int(row[1]) for row in conn.execute(
            "SELECT data_quality_status, COUNT(*) FROM farmer_registry GROUP BY data_quality_status"
        ).fetchall()}
        by_municipality = [dict(row) for row in conn.execute(
            """SELECT municipality, COUNT(*) AS record_count,
                      SUM(COALESCE(coconut_area_hectares, 0)) AS coconut_area_hectares,
                      SUM(COALESCE(tree_count, 0)) AS tree_count
               FROM farmer_registry GROUP BY municipality ORDER BY municipality"""
        ).fetchall()]
        flags = [dict(row) for row in conn.execute(
            """SELECT flag_code, severity, COUNT(*) AS count
               FROM farmer_quality_flags GROUP BY flag_code, severity ORDER BY count DESC, flag_code"""
        ).fetchall()]
    return {
        "total_records": total,
        "quality_status_counts": by_status,
        "municipality_summary": by_municipality,
        "quality_flag_counts": flags,
        "privacy_note": "Names are stored only in the protected farmer_identities table and are not returned by this endpoint.",
    }


def intercrop_income_assessment(*, database_path: Path | None = None) -> dict[str, Any]:
    assessment_path = Path(__file__).resolve().parents[2] / "data" / "reference" / "intercrop_income_assessment.json"
    assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    with connection(database_path) as conn:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intercrop_economic_profiles'").fetchone()
        profiles: list[dict[str, Any]] = []
        if exists:
            rows = conn.execute(
                """SELECT assessment_version, site_code, crop, record_count, area_stats_json,
                          seedling_stats_json, unit_price_stats_json, gross_income_year_stats_json,
                          gross_income_per_hectare_stats_json, reported_cost_stats_json,
                          frequency_labels_json, quality_flags_json
                   FROM intercrop_economic_profiles ORDER BY crop, site_code"""
            ).fetchall()
            for row in rows:
                item = dict(row)
                for key in (
                    "area_stats_json", "seedling_stats_json", "unit_price_stats_json",
                    "gross_income_year_stats_json", "gross_income_per_hectare_stats_json",
                    "reported_cost_stats_json", "frequency_labels_json", "quality_flags_json",
                ):
                    item[key.removesuffix("_json")] = json.loads(item.pop(key))
                profiles.append(item)
    return {
        "assessment_version": assessment["assessment_version"],
        "source_access_class": assessment["source_access_class"],
        "source_sheets": assessment["source_sheets"],
        "intercrop_record_count": assessment["intercrop_record_count"],
        "crop_profiles": assessment["crop_profiles"],
        "site_profiles": profiles or assessment["site_profiles"],
        "quality_findings": assessment["quality_findings"],
        "approved_uses": assessment["approved_uses"],
        "prohibited_or_deferred_uses": assessment["prohibited_or_deferred_uses"],
        "privacy": {
            "farmer_names_exposed": False,
            "row_level_records_exposed": False,
            "note": "Only sanitized aggregate profiles are returned.",
        },
    }
