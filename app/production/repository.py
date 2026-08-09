from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.data_foundation.repository import connection
from app.domain.production import ProductionActualInput, ProductionEngineOutput


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def save_output(output: ProductionEngineOutput, *, database_path: Path | None = None) -> None:
    forecast = output.forecast
    snapshot = output.feature_snapshot
    shadow = output.shadow_comparison
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO production_feature_snapshots(
                   id, weather_feature_set_id, weather_run_id, adapter_version, feature_order_json,
                   features_json, ordered_values_json, source_map_json, quality_flags_json,
                   warnings_json, feature_sha256, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(snapshot.feature_snapshot_id), str(snapshot.weather_feature_set_id), str(snapshot.weather_run_id),
                snapshot.feature_adapter_version, _json(snapshot.feature_order), _json(snapshot.features),
                _json(snapshot.ordered_values), _json(snapshot.source_map),
                _json([item.value for item in snapshot.quality_flags]), _json(snapshot.warnings),
                snapshot.feature_sha256, snapshot.created_at.isoformat(),
            ),
        )
        posterior = forecast.posterior_prediction.model_dump(mode="json") if forecast.posterior_prediction else None
        conn.execute(
            """INSERT INTO production_forecasts_v3(
                   id, farm_id, cell_id, feature_snapshot_id, product, horizon_type, estimate_period,
                   valid_from, valid_to, unit, raw_ml_prediction, variety_adjusted_prediction,
                   posterior_json, posterior_status, probability_of_decline, model_version,
                   feature_adapter_version, variety_id, variety_class, variety_adjustment_factor,
                   variety_adjustment_basis, provenance_json, data_notice, warnings_json, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(forecast.production_forecast_id), str(forecast.farm_id), str(forecast.cell_id) if forecast.cell_id else None,
                str(snapshot.feature_snapshot_id), forecast.product.value, forecast.horizon_type.value,
                forecast.estimate_period, forecast.valid_from.isoformat(), forecast.valid_to.isoformat(),
                forecast.unit.value, forecast.raw_ml_prediction, forecast.variety_adjusted_prediction,
                _json(posterior) if posterior else None, forecast.posterior_status, forecast.probability_of_decline,
                forecast.model_version, forecast.feature_adapter_version, forecast.variety_id,
                forecast.variety_class.value, forecast.variety_adjustment_factor, forecast.variety_adjustment_basis,
                _json(forecast.provenance.model_dump(mode="json")), output.data_notice, _json(output.warnings),
                forecast.created_at.isoformat(),
            ),
        )
        conn.executemany(
            """INSERT INTO production_product_estimates(
                   id, forecast_id, product, quantity, unit, estimate_kind, conversion_basis,
                   parameter_names_json, quality_flags_json
               ) VALUES (?,?,?,?,?,?,?,?,?)""",
            [
                (
                    str(uuid4()), str(forecast.production_forecast_id), item.product.value, item.quantity,
                    item.unit.value, item.estimate_kind, item.conversion_basis, _json(item.parameter_names),
                    _json([flag.value for flag in item.quality_flags]),
                )
                for item in forecast.product_estimates
            ],
        )
        conn.execute(
            """INSERT INTO production_shadow_comparisons(
                   id, forecast_id, status, legacy_prediction_tons, v3_raw_prediction_tons,
                   v3_adjusted_prediction_tons, raw_delta_tons, adjusted_delta_tons, legacy_method, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid4()), str(forecast.production_forecast_id), shadow.status,
                shadow.legacy_prediction_tons, shadow.v3_raw_prediction_tons,
                shadow.v3_variety_adjusted_prediction_tons, shadow.raw_delta_tons,
                shadow.adjusted_delta_tons, shadow.legacy_method, datetime.now(UTC).isoformat(),
            ),
        )


def _decode_forecast(row: Any, products: list[Any], shadow: Any) -> dict[str, Any]:
    item = dict(row)
    for key in ("provenance_json", "warnings_json", "posterior_json"):
        target = key.removesuffix("_json")
        item[target] = json.loads(item[key]) if item[key] else None
        item.pop(key, None)
    item["product_estimates"] = []
    for product in products:
        value = dict(product)
        value["parameter_names"] = json.loads(value.pop("parameter_names_json"))
        value["quality_flags"] = json.loads(value.pop("quality_flags_json"))
        item["product_estimates"].append(value)
    item["shadow_comparison"] = dict(shadow) if shadow else None
    return item


def get_forecast(forecast_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute("SELECT * FROM production_forecasts_v3 WHERE id = ?", (str(forecast_id),)).fetchone()
        if not row:
            return None
        products = conn.execute(
            """SELECT product, quantity, unit, estimate_kind, conversion_basis,
                      parameter_names_json, quality_flags_json
               FROM production_product_estimates WHERE forecast_id = ? ORDER BY product""",
            (str(forecast_id),),
        ).fetchall()
        shadow = conn.execute(
            """SELECT status, legacy_prediction_tons, v3_raw_prediction_tons,
                      v3_adjusted_prediction_tons, raw_delta_tons, adjusted_delta_tons, legacy_method
               FROM production_shadow_comparisons WHERE forecast_id = ?""",
            (str(forecast_id),),
        ).fetchone()
    return _decode_forecast(row, products, shadow)


def list_forecasts(*, farm_id: UUID | None = None, limit: int = 50, database_path: Path | None = None) -> list[dict[str, Any]]:
    where = "WHERE farm_id = ?" if farm_id else ""
    params: tuple[Any, ...] = (str(farm_id), limit) if farm_id else (limit,)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT id, farm_id, cell_id, product, horizon_type, valid_from, valid_to, unit,
                       raw_ml_prediction, variety_adjusted_prediction, posterior_status, model_version,
                       feature_adapter_version, variety_id, variety_class, variety_adjustment_factor,
                       variety_adjustment_basis, created_at
                FROM production_forecasts_v3 {where} ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def save_actual(actual: ProductionActualInput, *, database_path: Path | None = None) -> str:
    actual_id = str(uuid4())
    with connection(database_path) as conn:
        if actual.forecast_id:
            forecast = conn.execute(
                "SELECT farm_id FROM production_forecasts_v3 WHERE id = ?",
                (str(actual.forecast_id),),
            ).fetchone()
            if not forecast:
                raise KeyError("Production forecast not found")
            if forecast["farm_id"] != str(actual.farm_id):
                raise ValueError("Actual farm_id does not match the linked production forecast")
        conn.execute(
            """INSERT INTO production_actuals(
                   id, forecast_id, farm_id, product, period_start, period_end, quantity, unit,
                   source_type, notes, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                actual_id, str(actual.forecast_id) if actual.forecast_id else None, str(actual.farm_id),
                actual.product.value, actual.period_start.isoformat(), actual.period_end.isoformat(),
                actual.quantity, actual.unit.value, actual.source_type, actual.notes,
                datetime.now(UTC).isoformat(),
            ),
        )
    return actual_id


def forecast_performance(forecast_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any] | None:
    forecast = get_forecast(forecast_id, database_path=database_path)
    if not forecast:
        return None
    with connection(database_path) as conn:
        actuals = [dict(row) for row in conn.execute(
            "SELECT * FROM production_actuals WHERE forecast_id = ? ORDER BY period_end",
            (str(forecast_id),),
        ).fetchall()]
    compatible = [item for item in actuals if item["product"] == forecast["product"] and item["unit"] == forecast["unit"]]
    expected = forecast["variety_adjusted_prediction"]
    comparisons = []
    for item in compatible:
        error = item["quantity"] - expected if expected is not None else None
        comparisons.append({
            "actual_id": item["id"], "actual_quantity": item["quantity"], "unit": item["unit"],
            "error": error, "absolute_error": abs(error) if error is not None else None,
            "percentage_error": (error / item["quantity"] * 100.0) if error is not None and item["quantity"] else None,
        })
    return {
        "forecast_id": str(forecast_id),
        "prediction": expected,
        "unit": forecast["unit"],
        "compatible_actual_count": len(comparisons),
        "comparisons": comparisons,
        "note": "Performance is reported only when product and unit match exactly. Period alignment remains a validation responsibility.",
    }


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    tables = ("production_feature_snapshots", "production_forecasts_v3", "production_product_estimates", "production_shadow_comparisons", "production_actuals")
    with connection(database_path) as conn:
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}


def get_feature_snapshot(snapshot_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT * FROM production_feature_snapshots WHERE id = ?", (str(snapshot_id),)
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    for key in (
        "feature_order_json", "features_json", "ordered_values_json", "source_map_json",
        "quality_flags_json", "warnings_json",
    ):
        item[key.removesuffix("_json")] = json.loads(item.pop(key))
    return item
