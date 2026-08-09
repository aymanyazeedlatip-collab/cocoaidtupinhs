from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.data_foundation.repository import connection
from app.domain.bayesian import BayesianEngineOutput, BayesianEvidenceObservation


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def save_observation(observation: BayesianEvidenceObservation, *, database_path: Path | None = None) -> UUID:
    with connection(database_path) as conn:
        if observation.production_forecast_id:
            forecast = conn.execute(
                "SELECT farm_id, cell_id FROM production_forecasts_v3 WHERE id = ?",
                (str(observation.production_forecast_id),),
            ).fetchone()
            if not forecast:
                raise KeyError("Production forecast not found")
            if forecast["farm_id"] != str(observation.farm_id):
                raise ValueError("Evidence farm_id does not match the linked production forecast")
            if observation.cell_id and forecast["cell_id"] and forecast["cell_id"] != str(observation.cell_id):
                raise ValueError("Evidence cell_id does not match the linked production forecast")
        conn.execute(
            """INSERT INTO bayesian_evidence_observations(
                   id, farm_id, cell_id, production_forecast_id, evidence_type, evidence_status,
                   observed_at, value, unit, notes, source_label, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(observation.observation_id), str(observation.farm_id),
                str(observation.cell_id) if observation.cell_id else None,
                str(observation.production_forecast_id) if observation.production_forecast_id else None,
                observation.evidence_type.value, observation.evidence_status.value,
                observation.observed_at.isoformat(), observation.value, observation.unit.value,
                observation.notes, observation.source_label, observation.created_at.isoformat(),
            ),
        )
    return observation.observation_id


def _decode_observation(row: Any) -> dict[str, Any]:
    return dict(row)


def get_observation(observation_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT * FROM bayesian_evidence_observations WHERE id = ?", (str(observation_id),)
        ).fetchone()
    return _decode_observation(row) if row else None


def get_observations(
    observation_ids: list[UUID], *, database_path: Path | None = None,
) -> list[dict[str, Any]]:
    if not observation_ids:
        return []
    placeholders = ",".join("?" for _ in observation_ids)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM bayesian_evidence_observations WHERE id IN ({placeholders})",
            tuple(str(item) for item in observation_ids),
        ).fetchall()
    by_id = {row["id"]: _decode_observation(row) for row in rows}
    return [by_id[str(item)] for item in observation_ids if str(item) in by_id]


def list_observations(
    *, farm_id: UUID | None = None, limit: int = 100, database_path: Path | None = None,
) -> list[dict[str, Any]]:
    where = "WHERE farm_id = ?" if farm_id else ""
    params: tuple[Any, ...] = (str(farm_id), limit) if farm_id else (limit,)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM bayesian_evidence_observations {where} ORDER BY observed_at DESC, created_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [_decode_observation(row) for row in rows]


def save_output(
    output: BayesianEngineOutput,
    *, baseline_state_date: datetime,
    intervention: str,
    database_path: Path | None = None,
) -> None:
    posterior = output.posterior
    diagnostics = output.diagnostics
    run_id = posterior.provenance.run_id
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO bayesian_runs(
                   id, posterior_id, production_forecast_id, farm_id, cell_id, prior_posterior_id,
                   baseline_state_date, valid_at, horizon_months, particle_count, random_seed,
                   intervention, evidence_ids_json, diagnostics_json, data_notice, warnings_json, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(run_id), str(posterior.posterior_id),
                str(posterior.production_forecast_id) if posterior.production_forecast_id else None,
                str(posterior.farm_id), str(posterior.cell_id) if posterior.cell_id else None,
                str(posterior.prior_posterior_id) if posterior.prior_posterior_id else None,
                baseline_state_date.isoformat(), posterior.valid_at.isoformat(), posterior.horizon_months,
                diagnostics.particle_count, diagnostics.random_seed, intervention,
                _json([str(item) for item in posterior.evidence_observation_ids]),
                _json(diagnostics.model_dump(mode="json")), output.data_notice, _json(output.warnings),
                posterior.created_at.isoformat(),
            ),
        )
        conn.execute(
            """INSERT INTO bayesian_posteriors(
                   id, run_id, state_json, state_intervals_json, production_distribution_json,
                   base_production_tonnes, probability_of_decline, probability_of_recovery,
                   probability_of_tree_mortality, probability_of_pest_outbreak,
                   uncertainty_sources_json, provenance_json, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(posterior.posterior_id), str(run_id),
                _json(posterior.state.model_dump(mode="json")),
                _json([item.model_dump(mode="json") for item in posterior.state_intervals]),
                _json(posterior.production_distribution.model_dump(mode="json")),
                posterior.base_production_tonnes, posterior.probability_of_decline,
                posterior.probability_of_recovery, posterior.probability_of_tree_mortality,
                posterior.probability_of_pest_outbreak, _json(posterior.primary_uncertainty_sources),
                _json(posterior.provenance.model_dump(mode="json")), posterior.created_at.isoformat(),
            ),
        )
        conn.executemany(
            """INSERT INTO bayesian_parameter_posteriors(
                   posterior_id, name, distribution, parameters_json, posterior_mean, credible_interval_json
               ) VALUES (?,?,?,?,?,?)""",
            [
                (
                    str(posterior.posterior_id), item.name, item.distribution, _json(item.parameters),
                    item.posterior_mean,
                    _json(item.credible_interval.model_dump(mode="json")) if item.credible_interval else None,
                )
                for item in posterior.parameters
            ],
        )
        conn.executemany(
            """INSERT INTO bayesian_evidence_assimilation(
                   posterior_id, observation_id, evidence_type, evidence_status, used_for_update,
                   reliability_weight, ess_before, ess_after, resampled, explanation
               ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    str(posterior.posterior_id), str(item.observation_id), item.evidence_type.value,
                    item.evidence_status.value, int(item.used_for_update), item.reliability_weight,
                    item.effective_sample_size_before, item.effective_sample_size_after,
                    int(item.resampled), item.explanation,
                )
                for item in output.evidence_results
            ],
        )
        if posterior.production_forecast_id:
            conn.execute(
                """UPDATE production_forecasts_v3
                   SET posterior_json = ?, posterior_status = 'available', probability_of_decline = ?
                   WHERE id = ?""",
                (
                    _json(posterior.production_distribution.model_dump(mode="json")),
                    posterior.probability_of_decline, str(posterior.production_forecast_id),
                ),
            )


def _decode_posterior(conn: Any, row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in (
        "evidence_ids_json", "diagnostics_json", "warnings_json", "state_json", "state_intervals_json",
        "production_distribution_json", "uncertainty_sources_json", "provenance_json",
    ):
        target = key.removesuffix("_json")
        item[target] = json.loads(item.pop(key)) if item.get(key) else None
    parameters = conn.execute(
        """SELECT name, distribution, parameters_json, posterior_mean, credible_interval_json
           FROM bayesian_parameter_posteriors WHERE posterior_id = ? ORDER BY name""",
        (item["posterior_id"],),
    ).fetchall()
    item["parameters"] = [
        {
            "name": parameter["name"],
            "distribution": parameter["distribution"],
            "parameters": json.loads(parameter["parameters_json"]),
            "posterior_mean": parameter["posterior_mean"],
            "credible_interval": json.loads(parameter["credible_interval_json"]) if parameter["credible_interval_json"] else None,
        }
        for parameter in parameters
    ]
    evidence = conn.execute(
        """SELECT observation_id, evidence_type, evidence_status, used_for_update,
                  reliability_weight, ess_before, ess_after, resampled, explanation
           FROM bayesian_evidence_assimilation WHERE posterior_id = ? ORDER BY rowid""",
        (item["posterior_id"],),
    ).fetchall()
    item["evidence_results"] = [
        {**dict(value), "used_for_update": bool(value["used_for_update"]), "resampled": bool(value["resampled"])}
        for value in evidence
    ]
    return item


def get_posterior(posterior_id: str | UUID, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            """SELECT r.id AS run_id, r.posterior_id, r.production_forecast_id, r.farm_id, r.cell_id,
                      r.prior_posterior_id, r.baseline_state_date, r.valid_at, r.horizon_months,
                      r.particle_count, r.random_seed, r.intervention, r.evidence_ids_json,
                      r.diagnostics_json, r.data_notice, r.warnings_json, r.created_at,
                      p.state_json, p.state_intervals_json, p.production_distribution_json,
                      p.base_production_tonnes, p.probability_of_decline, p.probability_of_recovery,
                      p.probability_of_tree_mortality, p.probability_of_pest_outbreak,
                      p.uncertainty_sources_json, p.provenance_json
               FROM bayesian_runs r JOIN bayesian_posteriors p ON p.id = r.posterior_id
               WHERE r.posterior_id = ?""",
            (str(posterior_id),),
        ).fetchone()
        return _decode_posterior(conn, row) if row else None


def list_posteriors(
    *, farm_id: UUID | None = None, limit: int = 50, database_path: Path | None = None,
) -> list[dict[str, Any]]:
    where = "WHERE r.farm_id = ?" if farm_id else ""
    params: tuple[Any, ...] = (str(farm_id), limit) if farm_id else (limit,)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT r.posterior_id, r.production_forecast_id, r.farm_id, r.cell_id,
                       r.prior_posterior_id, r.valid_at, r.horizon_months, r.particle_count,
                       r.random_seed, r.intervention, r.created_at,
                       p.base_production_tonnes, p.probability_of_decline, p.probability_of_recovery,
                       p.probability_of_tree_mortality, p.probability_of_pest_outbreak,
                       p.production_distribution_json
                FROM bayesian_runs r JOIN bayesian_posteriors p ON p.id = r.posterior_id
                {where} ORDER BY r.created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["production_distribution"] = json.loads(item.pop("production_distribution_json"))
        result.append(item)
    return result


def prior_parameter_summaries(posterior_id: str | UUID, *, database_path: Path | None = None) -> dict[str, dict[str, float]]:
    with connection(database_path) as conn:
        rows = conn.execute(
            "SELECT name, parameters_json FROM bayesian_parameter_posteriors WHERE posterior_id = ?",
            (str(posterior_id),),
        ).fetchall()
    return {row["name"]: json.loads(row["parameters_json"]) for row in rows}


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    tables = (
        "bayesian_evidence_observations", "bayesian_runs", "bayesian_posteriors",
        "bayesian_parameter_posteriors", "bayesian_evidence_assimilation",
    )
    with connection(database_path) as conn:
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
