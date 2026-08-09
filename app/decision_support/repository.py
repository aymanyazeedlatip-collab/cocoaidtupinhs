from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.data_foundation.repository import connection
from app.domain.decision_support import DecisionSupportEngineOutput


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str, allow_nan=False)


def save_output(output: DecisionSupportEngineOutput, *, database_path: Path | None = None) -> None:
    record = output.record
    summary = output.summary
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO decision_support_runs(
                   id, farm_id, generated_at, status, requested_components_json,
                   production_forecast_id, posterior_id, pest_assessment_run_id,
                   intercropping_run_id, rehabilitation_plan_id, overview_json,
                   summary_json, parameter_version, dependency_graph_version,
                   provenance_json, warnings_json, data_notice, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(record.analysis_run_id), str(record.farm_id), record.generated_at.isoformat(),
                record.status, _json(record.requested_components),
                _record_id(record, "production"), _record_id(record, "bayesian"),
                _record_id(record, "pest"), _record_id(record, "intercropping"),
                _record_id(record, "rehabilitation"),
                _json(record.overview.model_dump(mode="json")),
                _json(summary.model_dump(mode="json")), output.parameter_version,
                output.dependency_graph_version, _json(record.provenance.model_dump(mode="json")),
                _json(record.warnings), record.data_notice, record.created_at.isoformat(),
            ),
        )
        for item in record.component_results:
            conn.execute(
                """INSERT INTO decision_support_components(
                       run_id, component, engine_id, status, record_id,
                       summary_json, warnings_json, errors_json
                   ) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    str(record.analysis_run_id), item.component, item.engine_id,
                    item.status, str(item.record_id) if item.record_id else None,
                    _json(item.summary), _json(item.warnings), _json(item.errors),
                ),
            )
        for index, recommendation in enumerate(record.recommendations, start=1):
            conn.execute(
                """INSERT INTO decision_support_recommendations(
                       id, run_id, sequence, category, priority, title, action,
                       rationale, confidence, source_components_json, evidence_json,
                       requires_field_confirmation, limitations_json, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(recommendation.recommendation_id), str(record.analysis_run_id), index,
                    recommendation.category, recommendation.priority, recommendation.title,
                    recommendation.action, recommendation.rationale, recommendation.confidence.value,
                    _json(recommendation.source_components),
                    _json([item.model_dump(mode="json") for item in recommendation.evidence]),
                    int(recommendation.requires_field_confirmation),
                    _json(recommendation.limitations), recommendation.created_at.isoformat(),
                ),
            )
        for index, edge in enumerate(record.traceability, start=1):
            conn.execute(
                """INSERT INTO decision_support_trace_edges(
                       run_id, sequence, upstream_component, downstream_component,
                       relationship, upstream_record_id, downstream_record_id
                   ) VALUES (?,?,?,?,?,?,?)""",
                (
                    str(record.analysis_run_id), index, edge.upstream_component,
                    edge.downstream_component, edge.relationship,
                    edge.upstream_record_id, edge.downstream_record_id,
                ),
            )


def _record_id(record, component: str) -> str | None:
    item = next((value for value in record.component_results if value.component == component), None)
    return str(item.record_id) if item and item.record_id else None


def _decode(conn, row) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    for key in ("requested_components_json", "overview_json", "summary_json", "provenance_json", "warnings_json"):
        item[key.removesuffix("_json")] = json.loads(item.pop(key))
    components = []
    for row_value in conn.execute(
        "SELECT * FROM decision_support_components WHERE run_id = ? ORDER BY rowid",
        (item["analysis_run_id"],),
    ).fetchall():
        value = dict(row_value)
        for key in ("summary_json", "warnings_json", "errors_json"):
            value[key.removesuffix("_json")] = json.loads(value.pop(key))
        components.append(value)
    recommendations = []
    for row_value in conn.execute(
        "SELECT * FROM decision_support_recommendations WHERE run_id = ? ORDER BY sequence",
        (item["analysis_run_id"],),
    ).fetchall():
        value = dict(row_value)
        for key in ("source_components_json", "evidence_json", "limitations_json"):
            value[key.removesuffix("_json")] = json.loads(value.pop(key))
        value["requires_field_confirmation"] = bool(value["requires_field_confirmation"])
        recommendations.append(value)
    traceability = [dict(value) for value in conn.execute(
        "SELECT * FROM decision_support_trace_edges WHERE run_id = ? ORDER BY sequence",
        (item["analysis_run_id"],),
    ).fetchall()]
    item["component_results"] = components
    item["recommendations"] = recommendations
    item["traceability"] = traceability
    return item


def get_run(run_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            """SELECT id AS analysis_run_id, farm_id, generated_at, status,
                      requested_components_json, production_forecast_id, posterior_id,
                      pest_assessment_run_id, intercropping_run_id, rehabilitation_plan_id,
                      overview_json, summary_json, parameter_version,
                      dependency_graph_version, provenance_json, warnings_json,
                      data_notice, created_at
               FROM decision_support_runs WHERE id = ?""",
            (str(run_id),),
        ).fetchone()
        return _decode(conn, row)


def list_runs(*, farm_id: UUID | None = None, limit: int = 100, database_path: Path | None = None) -> list[dict[str, Any]]:
    where = "WHERE farm_id = ?" if farm_id else ""
    params = (str(farm_id), limit) if farm_id else (limit,)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT id AS analysis_run_id, farm_id, generated_at, status,
                       production_forecast_id, posterior_id, pest_assessment_run_id,
                       intercropping_run_id, rehabilitation_plan_id, overview_json,
                       summary_json, parameter_version, created_at
                FROM decision_support_runs {where}
                ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["overview"] = json.loads(item.pop("overview_json"))
        item["summary"] = json.loads(item.pop("summary_json"))
        result.append(item)
    return result


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    tables = (
        "decision_support_runs", "decision_support_components",
        "decision_support_recommendations", "decision_support_trace_edges",
    )
    with connection(database_path) as conn:
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
