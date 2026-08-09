from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID, uuid4

from app.core.config import settings
from app.domain.weather import WeatherFeatureSet
from app.weather.assimilation.normalizer import NormalizedWeatherRun


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


def find_existing_run(run: NormalizedWeatherRun, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            """SELECT * FROM weather_model_runs
               WHERE raw_payload_sha256 = ? AND latitude = ? AND longitude = ? AND provider_model = ?
               ORDER BY retrieved_at DESC LIMIT 1""",
            (run.raw_payload_sha256, run.latitude, run.longitude, run.provider_model),
        ).fetchone()
    return dict(row) if row else None


def save_run(
    run: NormalizedWeatherRun,
    feature_set: WeatherFeatureSet | None,
    *,
    database_path: Path | None = None,
) -> tuple[str, str | None, bool]:
    existing = find_existing_run(run, database_path=database_path)
    if existing:
        existing_features = get_feature_set_for_run(existing["id"], database_path=database_path)
        return existing["id"], existing_features.get("id") if existing_features else None, True

    run_id = str(uuid4())
    feature_set_id: str | None = None
    created_at = datetime.now(UTC).isoformat()
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO weather_model_runs(
                   id, provider, provider_model, data_kind, latitude, longitude, timezone,
                   requested_forecast_days, requested_history_days, provider_run_at,
                   provider_run_time_basis, retrieved_at, valid_from, valid_to,
                   raw_payload_sha256, payload_json, units_json, quality_flags_json,
                   provider_metadata_json, is_stale, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, run.provider, run.provider_model, "forecast", run.latitude, run.longitude, run.timezone,
                run.requested_forecast_days, run.requested_history_days,
                run.provider_run_at.isoformat() if run.provider_run_at else None,
                run.provider_run_time_basis, run.retrieved_at.isoformat(), run.valid_from.isoformat(), run.valid_to.isoformat(),
                run.raw_payload_sha256, _json(run.payload_for_storage), _json(run.units), _json(run.quality_flags),
                _json(run.provider_metadata), int(run.is_stale), created_at,
            ),
        )
        conn.executemany(
            """INSERT INTO weather_values(
                   weather_run_id, valid_at, period_kind, resolution, variable, value, unit, quality_flags_json
               ) VALUES (?,?,?,?,?,?,?,?)""",
            [
                (run_id, item.valid_at.isoformat(), item.period_kind, item.resolution, item.variable, item.value, item.unit, _json(item.quality_flags))
                for item in run.values
            ],
        )
        if feature_set is not None:
            feature_set_id = str(feature_set.feature_set_id)
            conn.execute(
                """INSERT INTO weather_feature_sets(
                       id, weather_run_id, farm_id, latitude, longitude, valid_at, feature_adapter_version, created_at
                   ) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    feature_set_id, run_id, str(feature_set.farm_id) if feature_set.farm_id else None,
                    feature_set.latitude, feature_set.longitude, feature_set.valid_at.isoformat(),
                    feature_set.feature_adapter_version, feature_set.created_at.isoformat(),
                ),
            )
            conn.executemany(
                """INSERT INTO weather_features(
                       feature_set_id, name, value, unit, aggregation_window_days, derivation, quality_flags_json
                   ) VALUES (?,?,?,?,?,?,?)""",
                [
                    (
                        feature_set_id, item.name, item.value, item.unit.value, item.aggregation_window_days,
                        item.derivation, _json([flag.value for flag in item.quality_flags]),
                    )
                    for item in feature_set.features
                ],
            )
    return run_id, feature_set_id, False


def _decode_run(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for key in ("units_json", "quality_flags_json", "provider_metadata_json"):
        target = key.removesuffix("_json")
        item[target] = json.loads(item.pop(key))
    item.pop("payload_json", None)
    item["is_stale"] = bool(item["is_stale"])
    return item


def get_run(run_id: str | UUID, *, include_values: bool = False, period_kind: str | None = None, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute("SELECT * FROM weather_model_runs WHERE id = ?", (str(run_id),)).fetchone()
        if not row:
            return None
        result = _decode_run(row)
        if include_values:
            where = "WHERE weather_run_id = ?"
            params: list[Any] = [str(run_id)]
            if period_kind:
                where += " AND period_kind = ?"
                params.append(period_kind)
            values = conn.execute(
                f"""SELECT valid_at, period_kind, resolution, variable, value, unit, quality_flags_json
                    FROM weather_values {where} ORDER BY valid_at, resolution, variable""",
                tuple(params),
            ).fetchall()
            result["values"] = [
                {**dict(value), "quality_flags": json.loads(value["quality_flags_json"])} for value in values
            ]
            for value in result["values"]:
                value.pop("quality_flags_json", None)
    return result


def list_runs(*, limit: int = 50, latitude: float | None = None, longitude: float | None = None, database_path: Path | None = None) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if latitude is not None:
        clauses.append("ABS(latitude - ?) <= 0.01")
        params.append(latitude)
    if longitude is not None:
        clauses.append("ABS(longitude - ?) <= 0.01")
        params.append(longitude)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM weather_model_runs {where} ORDER BY retrieved_at DESC LIMIT ?", tuple(params)
        ).fetchall()
    return [_decode_run(row) for row in rows]


def get_feature_set(feature_set_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT * FROM weather_feature_sets WHERE id = ?", (str(feature_set_id),)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        values = conn.execute(
            """SELECT name, value, unit, aggregation_window_days, derivation, quality_flags_json
               FROM weather_features WHERE feature_set_id = ? ORDER BY name""", (str(feature_set_id),)
        ).fetchall()
    result["features"] = [
        {**dict(item), "quality_flags": json.loads(item["quality_flags_json"])} for item in values
    ]
    for item in result["features"]:
        item.pop("quality_flags_json", None)
    return result


def get_feature_set_for_run(run_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT * FROM weather_feature_sets WHERE weather_run_id = ? ORDER BY created_at DESC LIMIT 1", (str(run_id),)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        values = conn.execute(
            """SELECT name, value, unit, aggregation_window_days, derivation, quality_flags_json
               FROM weather_features WHERE feature_set_id = ? ORDER BY name""", (row["id"],)
        ).fetchall()
    result["features"] = [
        {**dict(item), "quality_flags": json.loads(item["quality_flags_json"])} for item in values
    ]
    for item in result["features"]:
        item.pop("quality_flags_json", None)
    return result


def summary(*, database_path: Path | None = None) -> dict[str, Any]:
    with connection(database_path) as conn:
        counts = {
            "weather_model_runs": int(conn.execute("SELECT COUNT(*) FROM weather_model_runs").fetchone()[0]),
            "weather_values": int(conn.execute("SELECT COUNT(*) FROM weather_values").fetchone()[0]),
            "weather_feature_sets": int(conn.execute("SELECT COUNT(*) FROM weather_feature_sets").fetchone()[0]),
            "weather_features": int(conn.execute("SELECT COUNT(*) FROM weather_features").fetchone()[0]),
        }
        latest = conn.execute("SELECT id, retrieved_at, valid_to, is_stale FROM weather_model_runs ORDER BY retrieved_at DESC LIMIT 1").fetchone()
    return {"counts": counts, "latest_run": ({**dict(latest), "is_stale": bool(latest["is_stale"]) } if latest else None)}


def compare_runs(base_run_id: str | UUID, comparison_run_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any]:
    base = get_run(base_run_id, database_path=database_path)
    comparison = get_run(comparison_run_id, database_path=database_path)
    if not base or not comparison:
        missing = str(base_run_id) if not base else str(comparison_run_id)
        raise KeyError(f"Weather run not found: {missing}")
    if abs(base["latitude"] - comparison["latitude"]) > 0.01 or abs(base["longitude"] - comparison["longitude"]) > 0.01:
        raise ValueError("Weather runs must represent the same location for comparison")

    variables = (
        "precipitation_sum", "temperature_2m_max", "temperature_2m_min",
        "wind_gusts_10m_max", "et0_fao_evapotranspiration",
    )
    placeholders = ",".join("?" for _ in variables)
    with connection(database_path) as conn:
        def values(run_id: str | UUID) -> dict[tuple[str, str], float]:
            rows = conn.execute(
                f"""SELECT valid_at, variable, value FROM weather_values
                    WHERE weather_run_id = ? AND resolution = 'daily' AND period_kind IN ('current','forecast')
                      AND variable IN ({placeholders}) AND value IS NOT NULL""",
                (str(run_id), *variables),
            ).fetchall()
            return {(row["valid_at"], row["variable"]): float(row["value"]) for row in rows}
        base_values = values(base_run_id)
        comparison_values = values(comparison_run_id)

    shared = sorted(set(base_values) & set(comparison_values))
    by_variable: dict[str, list[float]] = {}
    changes: list[dict[str, Any]] = []
    for valid_at, variable in shared:
        delta = comparison_values[(valid_at, variable)] - base_values[(valid_at, variable)]
        by_variable.setdefault(variable, []).append(delta)
        changes.append({
            "valid_at": valid_at, "variable": variable,
            "base": base_values[(valid_at, variable)],
            "comparison": comparison_values[(valid_at, variable)], "delta": delta,
        })
    metrics = {
        variable: {
            "shared_points": len(deltas),
            "mean_change": sum(deltas) / len(deltas),
            "mean_absolute_change": sum(abs(value) for value in deltas) / len(deltas),
            "maximum_absolute_change": max(abs(value) for value in deltas),
        }
        for variable, deltas in by_variable.items()
    }
    return {
        "base_run": base,
        "comparison_run": comparison,
        "shared_value_count": len(shared),
        "metrics": metrics,
        "changes": changes,
        "interpretation": "Positive deltas mean the newer comparison run predicts a higher value for the same valid date.",
    }
