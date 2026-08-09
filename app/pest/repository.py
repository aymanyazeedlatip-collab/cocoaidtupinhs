from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.bayesian import repository as bayesian_repository
from app.data_foundation.repository import connection
from app.domain.bayesian import BayesianEvidenceObservation
from app.domain.pest import PestEngineOutput, PestObservation


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def load_reference_profiles(
    pest_profile_ids: list[str] | None = None,
    *,
    database_path: Path | None = None,
) -> list[dict[str, Any]]:
    params: tuple[Any, ...] = ()
    where = ""
    if pest_profile_ids:
        placeholders = ",".join("?" for _ in pest_profile_ids)
        where = f"WHERE p.id IN ({placeholders})"
        params = tuple(pest_profile_ids)
    with connection(database_path) as conn:
        profiles = [dict(row) for row in conn.execute(
            f"""SELECT p.*, d.title AS source_title, d.sha256 AS source_sha256
                FROM pest_profiles p JOIN source_documents d ON d.id = p.source_document_id
                {where} ORDER BY p.common_name""",
            params,
        ).fetchall()]
        for profile in profiles:
            rules = conn.execute(
                """SELECT factor_code, direction, condition_json, likelihood_ratio, confidence,
                          source_document_id, source_page, explanation
                   FROM pest_evidence_rules WHERE pest_id = ? ORDER BY factor_code""",
                (profile["id"],),
            ).fetchall()
            actions = conn.execute(
                """SELECT action_type, timing, action_text, safety_notes, source_document_id, source_page
                   FROM pest_management_actions WHERE pest_id = ? ORDER BY action_type, id""",
                (profile["id"],),
            ).fetchall()
            profile["rules"] = [
                {**dict(item), "condition": json.loads(item["condition_json"])} for item in rules
            ]
            for item in profile["rules"]:
                item.pop("condition_json", None)
            profile["actions"] = [dict(item) for item in actions]
    return profiles


def save_observation(observation: PestObservation, *, database_path: Path | None = None) -> tuple[UUID, UUID | None]:
    bayesian_observation_id: UUID | None = None
    with connection(database_path) as conn:
        profile = conn.execute("SELECT id FROM pest_profiles WHERE id = ?", (observation.pest_profile_id,)).fetchone()
        if not profile:
            raise KeyError("Pest profile not found")
        if observation.production_forecast_id:
            forecast = conn.execute(
                "SELECT farm_id FROM production_forecasts_v3 WHERE id = ?",
                (str(observation.production_forecast_id),),
            ).fetchone()
            if not forecast:
                raise KeyError("Production forecast not found")
            if forecast["farm_id"] != str(observation.farm_id):
                raise ValueError("Observation farm_id does not match the linked production forecast")

    if observation.prevalence_fraction is not None:
        bayesian = BayesianEvidenceObservation(
            farm_id=observation.farm_id,
            cell_id=observation.cell_id,
            production_forecast_id=observation.production_forecast_id,
            evidence_type="pest_prevalence",
            evidence_status=observation.evidence_status,
            observed_at=observation.observed_at,
            value=observation.prevalence_fraction,
            unit="fraction",
            notes=(
                f"Linked Phase 6 pest observation for {observation.pest_profile_id}. "
                + (observation.notes or "")
            ).strip(),
            source_label=observation.source_label,
        )
        bayesian_observation_id = bayesian_repository.save_observation(bayesian, database_path=database_path)

    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO pest_observations_v3(
                   id, farm_id, cell_id, production_forecast_id, pest_profile_id, factor_code,
                   evidence_status, observed_at, value_json, unit, prevalence_fraction,
                   latitude, longitude, source_label, notes, bayesian_observation_id, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(observation.observation_id), str(observation.farm_id),
                str(observation.cell_id) if observation.cell_id else None,
                str(observation.production_forecast_id) if observation.production_forecast_id else None,
                observation.pest_profile_id, observation.factor_code, observation.evidence_status.value,
                observation.observed_at.isoformat(), _json(observation.value),
                observation.unit.value if observation.unit else None, observation.prevalence_fraction,
                observation.latitude, observation.longitude, observation.source_label, observation.notes,
                str(bayesian_observation_id) if bayesian_observation_id else None,
                observation.created_at.isoformat(),
            ),
        )
    return observation.observation_id, bayesian_observation_id


def _decode_observation(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["value"] = json.loads(item.pop("value_json"))
    return item


def get_observations(
    observation_ids: list[UUID],
    *,
    database_path: Path | None = None,
) -> list[dict[str, Any]]:
    if not observation_ids:
        return []
    placeholders = ",".join("?" for _ in observation_ids)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM pest_observations_v3 WHERE id IN ({placeholders}) ORDER BY observed_at, created_at",
            tuple(str(item) for item in observation_ids),
        ).fetchall()
    return [_decode_observation(row) for row in rows]


def list_observations(
    *,
    farm_id: UUID | None = None,
    pest_profile_id: str | None = None,
    limit: int = 100,
    database_path: Path | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if farm_id:
        clauses.append("farm_id = ?")
        params.append(str(farm_id))
    if pest_profile_id:
        clauses.append("pest_profile_id = ?")
        params.append(pest_profile_id)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM pest_observations_v3 {where} ORDER BY observed_at DESC, created_at DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    return [_decode_observation(row) for row in rows]


def save_output(
    output: PestEngineOutput,
    *,
    request_payload: dict[str, Any],
    database_path: Path | None = None,
) -> None:
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO pest_assessment_runs(
                   id, farm_id, cell_id, production_forecast_id, posterior_id,
                   weather_feature_set_id, weather_run_id, assessed_at, requested_pest_ids_json,
                   farm_context_json, observation_ids_json, nearby_cases_json, parameter_version,
                   data_notice, taxonomy_notice, warnings_json, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(output.run_id), request_payload["farm_id"], request_payload.get("cell_id"),
                request_payload["production_forecast_id"], request_payload.get("posterior_id"),
                str(output.weather_feature_set_id), str(output.weather_run_id), request_payload["assessed_at"],
                _json(request_payload["pest_profile_ids"]), _json(request_payload["context"]),
                _json(request_payload["observation_ids"]), _json(request_payload["nearby_confirmed_cases"]),
                output.parameter_version, output.data_notice, output.taxonomy_notice,
                _json(output.warnings), datetime.now(UTC).isoformat(),
            ),
        )
        for assessment in output.assessments:
            conn.execute(
                """INSERT INTO pest_assessments_v3(
                       id, run_id, pest_profile_id, outbreak_probability, risk_class,
                       severity_if_outbreak, exposed_palms, conditional_loss, expected_loss,
                       loss_unit, spatial_pressure, recommended_inspection_at, quarantine_warning,
                       profile_snapshot_json, provenance_json, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(assessment.assessment_id), str(output.run_id), assessment.profile.pest_profile_id,
                    assessment.outbreak_probability, assessment.risk_class, assessment.severity_if_outbreak,
                    assessment.exposed_palms, assessment.conditional_loss, assessment.expected_loss,
                    assessment.loss_unit.value, assessment.spatial_pressure,
                    assessment.recommended_inspection_at.isoformat(), assessment.quarantine_warning,
                    _json(assessment.profile.model_dump(mode="json")),
                    _json(assessment.provenance.model_dump(mode="json")), assessment.created_at.isoformat(),
                ),
            )
            conn.executemany(
                """INSERT INTO pest_assessment_contributions(
                       assessment_id, sequence, factor_code, source_kind, direction, matched,
                       likelihood_ratio, log_odds_delta, confidence, evidence_status, explanation,
                       source_document_id, source_page
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        str(assessment.assessment_id), item.sequence, item.factor_code, item.source_kind,
                        item.direction, int(item.matched), item.likelihood_ratio, item.log_odds_delta,
                        item.confidence.value, item.evidence_status.value if item.evidence_status else None,
                        item.explanation, item.source_document_id, item.source_page,
                    )
                    for item in assessment.evidence_contributions
                ],
            )
            conn.executemany(
                """INSERT INTO pest_assessment_actions(
                       assessment_id, sequence, action_type, timing, action_text, safety_notes,
                       source_document_id, source_page
                   ) VALUES (?,?,?,?,?,?,?,?)""",
                [
                    (
                        str(assessment.assessment_id), item.sequence, item.action_type, item.timing,
                        item.action_text, item.safety_notes, item.source_document_id, item.source_page,
                    )
                    for item in assessment.management_actions
                ],
            )


def _decode_assessment(conn: Any, row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in (
        "requested_pest_ids_json", "farm_context_json", "observation_ids_json", "nearby_cases_json",
        "warnings_json", "profile_snapshot_json", "provenance_json",
    ):
        item[key.removesuffix("_json")] = json.loads(item.pop(key))
    contributions = conn.execute(
        """SELECT sequence, factor_code, source_kind, direction, matched, likelihood_ratio,
                  log_odds_delta, confidence, evidence_status, explanation, source_document_id, source_page
           FROM pest_assessment_contributions WHERE assessment_id = ? ORDER BY sequence""",
        (item["assessment_id"],),
    ).fetchall()
    item["evidence_contributions"] = [
        {**dict(value), "matched": bool(value["matched"])} for value in contributions
    ]
    actions = conn.execute(
        """SELECT sequence, action_type, timing, action_text, safety_notes, source_document_id, source_page
           FROM pest_assessment_actions WHERE assessment_id = ? ORDER BY sequence""",
        (item["assessment_id"],),
    ).fetchall()
    item["management_actions"] = [dict(value) for value in actions]
    return item


def get_assessment(assessment_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            """SELECT a.id AS assessment_id, a.run_id, r.farm_id, r.cell_id,
                      r.production_forecast_id, r.posterior_id, r.weather_feature_set_id, r.weather_run_id,
                      r.assessed_at, r.requested_pest_ids_json, r.farm_context_json,
                      r.observation_ids_json, r.nearby_cases_json, r.parameter_version,
                      r.data_notice, r.taxonomy_notice, r.warnings_json,
                      a.pest_profile_id, a.outbreak_probability, a.risk_class,
                      a.severity_if_outbreak, a.exposed_palms, a.conditional_loss,
                      a.expected_loss, a.loss_unit, a.spatial_pressure, a.recommended_inspection_at,
                      a.quarantine_warning, a.profile_snapshot_json, a.provenance_json, a.created_at
               FROM pest_assessments_v3 a JOIN pest_assessment_runs r ON r.id = a.run_id
               WHERE a.id = ?""",
            (str(assessment_id),),
        ).fetchone()
        return _decode_assessment(conn, row) if row else None


def list_assessments(
    *,
    farm_id: UUID | None = None,
    pest_profile_id: str | None = None,
    limit: int = 100,
    database_path: Path | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if farm_id:
        clauses.append("r.farm_id = ?")
        params.append(str(farm_id))
    if pest_profile_id:
        clauses.append("a.pest_profile_id = ?")
        params.append(pest_profile_id)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT a.id AS assessment_id, a.run_id, r.farm_id, r.cell_id,
                       r.production_forecast_id, r.posterior_id, r.assessed_at,
                       a.pest_profile_id, a.outbreak_probability, a.risk_class,
                       a.severity_if_outbreak, a.exposed_palms, a.conditional_loss,
                       a.expected_loss, a.loss_unit, a.spatial_pressure,
                       a.recommended_inspection_at, a.quarantine_warning, a.created_at
                FROM pest_assessments_v3 a JOIN pest_assessment_runs r ON r.id = a.run_id
                {where} ORDER BY a.created_at DESC LIMIT ?""",
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    tables = (
        "pest_observations_v3", "pest_assessment_runs", "pest_assessments_v3",
        "pest_assessment_contributions", "pest_assessment_actions",
    )
    with connection(database_path) as conn:
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
