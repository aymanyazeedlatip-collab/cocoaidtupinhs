from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

from app.core.config import settings
from app.domain.intercropping import IntercropEngineOutput


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


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str, allow_nan=False)


def load_candidates(candidate_ids: list[str] | None = None, *, database_path: Path | None = None) -> list[dict[str, Any]]:
    clauses = ""
    params: tuple[Any, ...] = ()
    if candidate_ids:
        placeholders = ",".join("?" for _ in candidate_ids)
        clauses = f"WHERE c.id IN ({placeholders})"
        params = tuple(candidate_ids)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT c.id, c.common_name, c.scientific_name, c.light_group,
                       c.min_light_fraction, c.max_light_fraction, c.confidence,
                       c.source_document_id, c.source_page, c.notes,
                       r.profile_version, r.min_temperature_c, r.max_temperature_c,
                       r.min_rainfall_mm_year, r.max_rainfall_mm_year,
                       r.min_soil_ph, r.max_soil_ph,
                       r.min_soil_moisture_index, r.max_soil_moisture_index,
                       r.min_drainage_index, r.water_demand, r.root_competition,
                       r.space_demand, r.nutrient_demand, r.management_demand,
                       r.pest_conflict_ids_json, r.beneficial_pest_ids_json,
                       r.economic_profile_crop, r.planting_months_json,
                       r.harvest_months_json, r.confidence AS requirement_confidence,
                       r.basis, r.notes AS requirement_notes
                FROM intercrop_candidates c
                JOIN intercrop_requirement_profiles r ON r.candidate_id = c.id
                {clauses}
                ORDER BY c.light_group, c.common_name""",
            params,
        ).fetchall()
    items=[]
    for row in rows:
        item=dict(row)
        for key in ("pest_conflict_ids_json","beneficial_pest_ids_json","planting_months_json","harvest_months_json"):
            item[key.removesuffix("_json")]=json.loads(item.pop(key))
        items.append(item)
    return items


def load_canopy_parameters(*, database_path: Path | None = None) -> list[dict[str, Any]]:
    with connection(database_path) as conn:
        return [dict(row) for row in conn.execute(
            """SELECT id, spacing_label, design, spacing_x_m, spacing_y_m,
                      palms_per_hectare, palm_age_years, transmitted_light_fraction,
                      suitable_crop_groups, confidence, source_document_id, source_page
               FROM canopy_light_parameters ORDER BY design, spacing_x_m, spacing_y_m, palm_age_years"""
        ).fetchall()]


def load_crop_economic_profiles(*, database_path: Path | None = None) -> dict[str, dict[str, Any]]:
    with connection(database_path) as conn:
        rows=conn.execute(
            """SELECT crop, SUM(record_count) AS record_count,
                      gross_income_per_hectare_stats_json, quality_flags_json
               FROM intercrop_economic_profiles GROUP BY crop
               ORDER BY crop"""
        ).fetchall()
    # The canonical aggregate profile in data/reference is preferred by the engine;
    # this method is retained for database availability checks and API summaries.
    result={}
    for row in rows:
        result[row["crop"]]={
            "record_count": int(row["record_count"]),
            "gross_income_per_hectare_php": json.loads(row["gross_income_per_hectare_stats_json"]),
            "quality_flags": json.loads(row["quality_flags_json"]),
        }
    return result


def load_pest_run(run_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        run=conn.execute("SELECT * FROM pest_assessment_runs WHERE id = ?",(str(run_id),)).fetchone()
        if not run:
            return None
        assessments=conn.execute(
            """SELECT pest_profile_id, outbreak_probability, risk_class, severity_if_outbreak
               FROM pest_assessments_v3 WHERE run_id = ? ORDER BY pest_profile_id""",
            (str(run_id),),
        ).fetchall()
    item=dict(run)
    item["assessments"]=[dict(row) for row in assessments]
    return item


def save_output(
    output: IntercropEngineOutput,
    *,
    request_payload: dict[str, Any],
    database_path: Path | None = None,
) -> None:
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO intercrop_assessment_runs(
                   id, farm_id, production_forecast_id, posterior_id, pest_assessment_run_id,
                   weather_feature_set_id, weather_run_id, assessed_at, candidate_ids_json,
                   cell_contexts_json, parameter_version, requirement_profile_version,
                   data_notice, warnings_json, summary_json, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(output.run_id), request_payload["farm_id"], request_payload["production_forecast_id"],
                request_payload.get("posterior_id"), request_payload.get("pest_assessment_run_id"),
                str(output.weather_feature_set_id), str(output.weather_run_id), request_payload["assessed_at"],
                _json(request_payload["candidate_ids"]), _json(request_payload["cells"]),
                output.parameter_version, output.requirement_profile_version,
                output.data_notice, _json(output.warnings), _json(output.summary.model_dump(mode="json")),
                output.created_at.isoformat(),
            ),
        )
        for assessment in output.assessments:
            conn.execute(
                """INSERT INTO intercrop_cell_assessments(
                       id, run_id, cell_id, cell_label, candidate_id, suitability_score,
                       suitability_class, hard_constraint_passed, canopy_light_json,
                       coconut_competition_risk, pest_conflict_risk, limiting_factors_json,
                       planting_window_start, planting_window_end, recommended_layout,
                       economic_potential_json, confidence, data_quality_notes_json,
                       candidate_snapshot_json, provenance_json, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(assessment.assessment_id), str(output.run_id), str(assessment.cell_id), assessment.cell_label,
                    assessment.candidate.candidate_id, assessment.suitability_score, assessment.suitability_class,
                    int(assessment.hard_constraint_passed), _json(assessment.canopy_light.model_dump(mode="json")),
                    assessment.coconut_competition_risk, assessment.pest_conflict_risk,
                    _json(assessment.limiting_factors),
                    assessment.planting_window_start.isoformat() if assessment.planting_window_start else None,
                    assessment.planting_window_end.isoformat() if assessment.planting_window_end else None,
                    assessment.recommended_layout,
                    _json(assessment.economic_potential.model_dump(mode="json")), assessment.confidence.value,
                    _json(assessment.data_quality_notes), _json(assessment.candidate.model_dump(mode="json")),
                    _json(assessment.provenance.model_dump(mode="json")), assessment.created_at.isoformat(),
                ),
            )
            conn.executemany(
                """INSERT INTO intercrop_component_scores(
                       assessment_id, sequence, factor, score, weight,
                       hard_constraint_passed, explanation
                   ) VALUES (?,?,?,?,?,?,?)""",
                [
                    (
                        str(assessment.assessment_id), index, component.factor, component.score,
                        component.weight, int(component.hard_constraint_passed), component.explanation,
                    )
                    for index, component in enumerate(assessment.components, start=1)
                ],
            )


def _decode_assessment(conn: sqlite3.Connection, row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item=dict(row)
    for key in (
        "canopy_light_json","limiting_factors_json","economic_potential_json",
        "data_quality_notes_json","candidate_snapshot_json","provenance_json",
    ):
        item[key.removesuffix("_json")]=json.loads(item.pop(key))
    item["hard_constraint_passed"]=bool(item["hard_constraint_passed"])
    item["components"]=[dict(component) for component in conn.execute(
        """SELECT sequence, factor, score, weight, hard_constraint_passed, explanation
           FROM intercrop_component_scores WHERE assessment_id = ? ORDER BY sequence""",
        (item["assessment_id"],),
    ).fetchall()]
    for component in item["components"]:
        component["hard_constraint_passed"]=bool(component["hard_constraint_passed"])
    return item


def get_assessment(assessment_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row=conn.execute(
            """SELECT a.id AS assessment_id, a.run_id, r.farm_id, r.production_forecast_id,
                      r.posterior_id, r.pest_assessment_run_id, r.assessed_at,
                      a.cell_id, a.cell_label, a.candidate_id, a.suitability_score,
                      a.suitability_class, a.hard_constraint_passed, a.canopy_light_json,
                      a.coconut_competition_risk, a.pest_conflict_risk,
                      a.limiting_factors_json, a.planting_window_start, a.planting_window_end,
                      a.recommended_layout, a.economic_potential_json, a.confidence,
                      a.data_quality_notes_json, a.candidate_snapshot_json,
                      a.provenance_json, a.created_at
               FROM intercrop_cell_assessments a
               JOIN intercrop_assessment_runs r ON r.id = a.run_id
               WHERE a.id = ?""",
            (str(assessment_id),),
        ).fetchone()
        return _decode_assessment(conn,row)


def list_assessments(
    *,
    farm_id: UUID | None = None,
    candidate_id: str | None = None,
    cell_id: UUID | None = None,
    limit: int = 200,
    database_path: Path | None = None,
) -> list[dict[str, Any]]:
    clauses=[]; params=[]
    if farm_id:
        clauses.append("r.farm_id = ?"); params.append(str(farm_id))
    if candidate_id:
        clauses.append("a.candidate_id = ?"); params.append(candidate_id)
    if cell_id:
        clauses.append("a.cell_id = ?"); params.append(str(cell_id))
    where="WHERE "+" AND ".join(clauses) if clauses else ""
    params.append(limit)
    with connection(database_path) as conn:
        rows=conn.execute(
            f"""SELECT a.id AS assessment_id, a.run_id, r.farm_id, r.production_forecast_id,
                       a.cell_id, a.cell_label, a.candidate_id, a.suitability_score,
                       a.suitability_class, a.hard_constraint_passed,
                       a.coconut_competition_risk, a.pest_conflict_risk,
                       a.confidence, a.created_at
                FROM intercrop_cell_assessments a
                JOIN intercrop_assessment_runs r ON r.id = a.run_id
                {where} ORDER BY a.created_at DESC, a.suitability_score DESC LIMIT ?""",
            tuple(params),
        ).fetchall()
    return [{**dict(row),"hard_constraint_passed":bool(row["hard_constraint_passed"])} for row in rows]


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    tables=("intercrop_requirement_profiles","intercrop_assessment_runs","intercrop_cell_assessments","intercrop_component_scores")
    with connection(database_path) as conn:
        return {table:int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
