from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.farm import FarmCreate, FarmRecord
from app.services.supabase_state import supabase_state


def _connect() -> sqlite3.Connection:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _connection():
    """Yield a transactional SQLite connection and always close it."""
    conn = _connect()
    before_changes = conn.total_changes
    try:
        yield conn
        conn.commit()
        if conn.total_changes > before_changes:
            supabase_state.request_sync()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> None:
    """Apply versioned schema migrations without deleting legacy records."""
    from app.storage.migrations import MigrationManager

    MigrationManager(settings.database_path).upgrade()


def _farm_from_row(row: sqlite3.Row) -> FarmRecord:
    payload = json.loads(row["payload"])
    return FarmRecord(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        **payload,
    )


def create_farm(farm: FarmCreate) -> FarmRecord:
    farm_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _connection() as conn:
        conn.execute(
            "INSERT INTO farms (id, payload, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (farm_id, farm.model_dump_json(), now, now),
        )
    return FarmRecord(id=farm_id, created_at=datetime.fromisoformat(now), updated_at=datetime.fromisoformat(now), **farm.model_dump())


def list_farms() -> list[FarmRecord]:
    with _connection() as conn:
        rows = conn.execute("SELECT * FROM farms ORDER BY updated_at DESC").fetchall()
    return [_farm_from_row(row) for row in rows]


def get_farm(farm_id: str) -> FarmRecord | None:
    with _connection() as conn:
        row = conn.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone()
    return _farm_from_row(row) if row else None


def update_farm(farm_id: str, farm: FarmCreate) -> FarmRecord | None:
    if get_farm(farm_id) is None:
        return None
    now = datetime.now(UTC).isoformat()
    with _connection() as conn:
        conn.execute("UPDATE farms SET payload = ?, updated_at = ? WHERE id = ?", (farm.model_dump_json(), now, farm_id))
    return get_farm(farm_id)


def delete_farm(farm_id: str) -> bool:
    with _connection() as conn:
        cursor = conn.execute("DELETE FROM farms WHERE id = ?", (farm_id,))
    return cursor.rowcount > 0


def save_analysis(input_payload: dict[str, Any], result_payload: dict[str, Any], metadata_payload: dict[str, Any]) -> str:
    analysis_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _connection() as conn:
        conn.execute(
            "INSERT INTO analyses (id, input_payload, result_payload, metadata_payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (analysis_id, json.dumps(input_payload, default=str), json.dumps(result_payload, default=str), json.dumps(metadata_payload, default=str), now),
        )
    return analysis_id


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    with _connection() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "input": json.loads(row["input_payload"]),
        "result": json.loads(row["result_payload"]),
        "metadata": json.loads(row["metadata_payload"]),
    }


def list_analyses(limit: int = 100) -> list[dict[str, Any]]:
    with _connection() as conn:
        rows = conn.execute("SELECT id, input_payload, result_payload, metadata_payload, created_at FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    items = []
    for row in rows:
        inputs = json.loads(row["input_payload"])
        result = json.loads(row["result_payload"])
        farm = inputs.get("farm", {})
        overview = result.get("overview", {})
        items.append({
            "id": row["id"], "created_at": row["created_at"],
            "farm_name": farm.get("name", "Analysis"),
            "scenario": inputs.get("scenario"), "end_year": inputs.get("end_year"),
            "recommended_intervention": overview.get("recommended_intervention"),
            "projected_end_median_tons": overview.get("projected_end_median_tons"),
        })
    return items


def delete_analysis(analysis_id: str) -> bool:
    with _connection() as conn:
        cursor = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    return cursor.rowcount > 0


def save_report(report_id: str, filepath: Path, analysis_id: str | None = None, report_type: str = "pdf") -> None:
    with _connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO reports (id, analysis_id, report_type, filepath, created_at) VALUES (?, ?, ?, ?, ?)",
            (report_id, analysis_id, report_type, str(filepath), datetime.now(UTC).isoformat()),
        )
    # Reports are persisted separately from the SQLite snapshot so a Render Free
    # cold start can restore the generated file lazily.
    if filepath.exists():
        supabase_state.upload_runtime_file(filepath, namespace="reports")


def get_report(report_id: str) -> Path | None:
    with _connection() as conn:
        row = conn.execute("SELECT filepath FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        return None
    path = Path(row["filepath"])
    if not path.exists():
        supabase_state.restore_runtime_file(path, namespace="reports")
    return path


def report_record(report_id: str) -> dict[str, Any] | None:
    with _connection() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return dict(row) if row else None


def list_reports(limit: int = 100) -> list[dict[str, Any]]:
    with _connection() as conn:
        rows = conn.execute("SELECT id, analysis_id, report_type, filepath, created_at FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [
        {"id": row["id"], "analysis_id": row["analysis_id"], "report_type": row["report_type"], "filename": Path(row["filepath"]).name, "created_at": row["created_at"]}
        for row in rows
    ]


def save_forecast(name: str, forecast_payload: dict[str, Any], summary_payload: dict[str, Any], farm_id: str | None = None, forecast_id: str | None = None) -> str:
    now = datetime.now(UTC).isoformat()
    identifier = forecast_id or str(uuid.uuid4())
    with _connection() as conn:
        conn.execute(
            """
            INSERT INTO saved_forecasts (id, farm_id, name, summary_payload, forecast_payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET farm_id=excluded.farm_id, name=excluded.name,
            summary_payload=excluded.summary_payload, forecast_payload=excluded.forecast_payload,
            updated_at=excluded.updated_at
            """,
            (identifier, farm_id, name[:160], json.dumps(summary_payload, default=str), json.dumps(forecast_payload, default=str), now, now),
        )
    return identifier


def list_forecasts(limit: int = 100) -> list[dict[str, Any]]:
    with _connection() as conn:
        rows = conn.execute("SELECT id, farm_id, name, summary_payload, created_at, updated_at FROM saved_forecasts ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return [
        {"id": row["id"], "farm_id": row["farm_id"], "name": row["name"], "summary": json.loads(row["summary_payload"]), "created_at": row["created_at"], "updated_at": row["updated_at"]}
        for row in rows
    ]


def get_forecast(forecast_id: str) -> dict[str, Any] | None:
    with _connection() as conn:
        row = conn.execute("SELECT * FROM saved_forecasts WHERE id = ?", (forecast_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"], "farm_id": row["farm_id"], "name": row["name"],
        "summary": json.loads(row["summary_payload"]), "forecast": json.loads(row["forecast_payload"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def delete_forecast(forecast_id: str) -> bool:
    with _connection() as conn:
        cursor = conn.execute("DELETE FROM saved_forecasts WHERE id = ?", (forecast_id,))
    return cursor.rowcount > 0


def database_summary() -> dict[str, int]:
    with _connection() as conn:
        return {
            "farms": int(conn.execute("SELECT COUNT(*) FROM farms").fetchone()[0]),
            "analyses": int(conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]),
            "forecasts": int(conn.execute("SELECT COUNT(*) FROM saved_forecasts").fetchone()[0]),
            "reports": int(conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]),
        }


initialize_database()
