from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.data_foundation.repository import connection
from app.domain.coco_pilot import CocoPilotResponse, FormalReportRecord


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str, allow_nan=False)


def save_response(response: CocoPilotResponse, *, database_path: Path | None = None) -> None:
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO coco_pilot_runs(
                   id, analysis_run_id, mode, provider, provider_model, status,
                   conclusion, bullets_json, action_line, full_text, citations_json,
                   source_manifest_json, redaction_summary_json, warnings_json,
                   limitations_json, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(response.run_id), str(response.analysis_run_id), response.mode,
                response.provider, response.provider_model, response.status,
                response.conclusion, _json(response.bullets), response.action_line,
                response.full_text,
                _json([item.model_dump(mode="json") for item in response.citations]),
                _json(response.source_manifest),
                _json(response.redaction_summary.model_dump(mode="json")),
                _json(response.warnings), _json(response.limitations),
                response.created_at.isoformat(),
            ),
        )


def get_response(run_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute("SELECT * FROM coco_pilot_runs WHERE id = ?", (str(run_id),)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["run_id"] = item.pop("id")
    for key in (
        "bullets_json", "citations_json", "source_manifest_json", "redaction_summary_json",
        "warnings_json", "limitations_json",
    ):
        item[key.removesuffix("_json")] = json.loads(item.pop(key))
    return item


def list_responses(
    *, analysis_run_id: UUID | None = None, limit: int = 100, database_path: Path | None = None,
) -> list[dict[str, Any]]:
    where = "WHERE analysis_run_id = ?" if analysis_run_id else ""
    params = (str(analysis_run_id), limit) if analysis_run_id else (limit,)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT id AS run_id, analysis_run_id, mode, provider, provider_model,
                       status, conclusion, action_line, warnings_json, created_at
                FROM coco_pilot_runs {where} ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["warnings"] = json.loads(item.pop("warnings_json"))
        result.append(item)
    return result


def save_report(record: FormalReportRecord, filepath: Path, *, database_path: Path | None = None) -> None:
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO formal_report_runs(
                   id, analysis_run_id, narrative_run_id, report_format, filename,
                   filepath, file_sha256, content_fingerprint, generator_version,
                   source_manifest_json, warnings_json, data_notice, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(record.report_id), str(record.analysis_run_id),
                str(record.narrative_run_id) if record.narrative_run_id else None,
                record.report_format, record.filename, str(filepath), record.file_sha256,
                record.content_fingerprint, record.generator_version,
                _json(record.source_manifest), _json(record.warnings), record.data_notice,
                record.created_at.isoformat(),
            ),
        )


def get_report(report_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute("SELECT * FROM formal_report_runs WHERE id = ?", (str(report_id),)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["report_id"] = item.pop("id")
    item["source_manifest"] = json.loads(item.pop("source_manifest_json"))
    item["warnings"] = json.loads(item.pop("warnings_json"))
    return item


def list_reports(
    *, analysis_run_id: UUID | None = None, limit: int = 100, database_path: Path | None = None,
) -> list[dict[str, Any]]:
    where = "WHERE analysis_run_id = ?" if analysis_run_id else ""
    params = (str(analysis_run_id), limit) if analysis_run_id else (limit,)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT id AS report_id, analysis_run_id, narrative_run_id, report_format,
                       filename, file_sha256, content_fingerprint, generator_version,
                       warnings_json, created_at
                FROM formal_report_runs {where} ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["warnings"] = json.loads(item.pop("warnings_json"))
        result.append(item)
    return result


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    with connection(database_path) as conn:
        return {
            "coco_pilot_runs": int(conn.execute("SELECT COUNT(*) FROM coco_pilot_runs").fetchone()[0]),
            "formal_report_runs": int(conn.execute("SELECT COUNT(*) FROM formal_report_runs").fetchone()[0]),
        }
