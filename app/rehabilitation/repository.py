from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.data_foundation.repository import connection
from app.domain.rehabilitation import RehabilitationEngineOutput


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str, allow_nan=False)


def load_pest_run(run_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        run = conn.execute("SELECT * FROM pest_assessment_runs WHERE id = ?", (str(run_id),)).fetchone()
        if not run:
            return None
        assessments = [dict(row) for row in conn.execute(
            """SELECT id AS assessment_id, pest_profile_id, outbreak_probability,
                      conditional_loss, expected_loss, loss_unit, risk_class
               FROM pest_assessments_v3 WHERE run_id = ? ORDER BY outbreak_probability DESC""",
            (str(run_id),),
        ).fetchall()]
        observation_ids = json.loads(run["observation_ids_json"])
        observations: list[dict[str, Any]] = []
        if observation_ids:
            placeholders = ",".join("?" for _ in observation_ids)
            observations = [dict(row) for row in conn.execute(
                f"SELECT id, evidence_status, pest_profile_id, prevalence_fraction FROM pest_observations_v3 WHERE id IN ({placeholders})",
                tuple(observation_ids),
            ).fetchall()]
    item = dict(run)
    item["assessments"] = assessments
    item["observations"] = observations
    return item


def load_intercropping_run(run_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        run = conn.execute("SELECT * FROM intercrop_assessment_runs WHERE id = ?", (str(run_id),)).fetchone()
        if not run:
            return None
        rows = conn.execute(
            """SELECT id AS assessment_id, cell_id, cell_label, candidate_id,
                      suitability_score, suitability_class, hard_constraint_passed,
                      economic_potential_json, confidence
               FROM intercrop_cell_assessments WHERE run_id = ?
               ORDER BY cell_id, suitability_score DESC""",
            (str(run_id),),
        ).fetchall()
    assessments = []
    for row in rows:
        item = dict(row)
        item["hard_constraint_passed"] = bool(item["hard_constraint_passed"])
        item["economic_potential"] = json.loads(item.pop("economic_potential_json"))
        assessments.append(item)
    return {**dict(run), "assessments": assessments}


def save_output(
    output: RehabilitationEngineOutput,
    *,
    request_payload: dict[str, Any],
    database_path: Path | None = None,
) -> None:
    plan = output.plan
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO rehabilitation_plan_runs(
                   id, farm_id, production_forecast_id, posterior_id, pest_assessment_run_id,
                   intercropping_run_id, planned_at, cell_contexts_json, total_budget_php,
                   available_labor_person_days, planning_horizon_months, annual_discount_rate,
                   risk_aversion, farm_data_version, parameter_version, cost_catalog_version,
                   linked_weather_run_id, selected_scenario, total_expected_cost_php,
                   unallocated_budget_php, summary_json, warnings_json, data_notice,
                   provenance_json, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(plan.rehabilitation_plan_id), str(plan.farm_id),
                str(plan.production_forecast_id) if plan.production_forecast_id else None,
                str(plan.posterior_id) if plan.posterior_id else None,
                str(plan.pest_assessment_run_id) if plan.pest_assessment_run_id else None,
                str(plan.intercropping_run_id) if plan.intercropping_run_id else None,
                request_payload["planned_at"], _json(request_payload["cells"]),
                plan.total_budget_php, request_payload.get("available_labor_person_days"),
                request_payload["planning_horizon_months"], request_payload["annual_discount_rate"],
                request_payload["risk_aversion"], request_payload["farm_data_version"],
                output.parameter_version, output.cost_catalog_version,
                str(output.linked_weather_run_id) if output.linked_weather_run_id else None,
                plan.selected_scenario, plan.total_expected_cost_php, plan.unallocated_budget_php,
                _json(output.summary.model_dump(mode="json")), _json(output.warnings), plan.data_notice,
                _json(plan.provenance.model_dump(mode="json")), plan.created_at.isoformat(),
            ),
        )
        for action in plan.actions:
            conn.execute(
                """INSERT INTO rehabilitation_actions_v3(
                       id, plan_id, cell_id, action_type, timing, priority,
                       problem_detected, likely_cause, triggers_json, evidence_ids_json,
                       instructions_json, required_materials_json, scheduled_date,
                       follow_up_dates_json, materials_php, labor_php, other_php,
                       total_php, labor_person_days, cost_basis, expected_recovery_days,
                       expected_production_regained_lower, expected_production_regained_median,
                       expected_production_regained_upper, production_regained_unit,
                       confidence, requires_field_confirmation, parameter_basis, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(action.action_id), str(plan.rehabilitation_plan_id),
                    str(action.cell_id) if action.cell_id else None, action.action_type.value,
                    action.timing.value, action.priority, action.problem_detected,
                    action.likely_cause, _json([item.model_dump(mode="json") for item in action.triggers]),
                    _json([str(item) for item in action.evidence_ids]), _json(action.instructions),
                    _json(action.required_materials), action.scheduled_date.isoformat() if action.scheduled_date else None,
                    _json([item.isoformat() for item in action.follow_up_dates]),
                    action.cost.materials_php, action.cost.labor_php, action.cost.other_php,
                    action.cost.total_php, action.cost.labor_person_days, action.cost.basis,
                    action.expected_recovery_days, action.expected_production_regained_lower,
                    action.expected_production_regained_median, action.expected_production_regained_upper,
                    action.production_regained_unit.value if action.production_regained_unit else None,
                    action.confidence.value, int(action.requires_field_confirmation),
                    action.parameter_basis, plan.created_at.isoformat(),
                ),
            )
        for scenario in plan.scenarios:
            conn.execute(
                """INSERT INTO rehabilitation_scenario_results(
                       id, plan_id, scenario_type, status, action_ids_json, total_cost_php,
                       labor_person_days, coconut_production_lower_tonnes,
                       coconut_production_median_tonnes, coconut_production_upper_tonnes,
                       intercrop_gross_revenue_lower_php, intercrop_gross_revenue_median_php,
                       intercrop_gross_revenue_upper_php, severe_loss_probability,
                       expected_utility, utility_components_json, feasibility_reasons_json,
                       assumptions_json, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(scenario.scenario_id), str(plan.rehabilitation_plan_id),
                    scenario.scenario_type, scenario.status,
                    _json([str(item) for item in scenario.action_ids]), scenario.total_cost_php,
                    scenario.labor_person_days, scenario.coconut_production_lower_tonnes,
                    scenario.coconut_production_median_tonnes, scenario.coconut_production_upper_tonnes,
                    scenario.intercrop_gross_revenue_lower_php,
                    scenario.intercrop_gross_revenue_median_php,
                    scenario.intercrop_gross_revenue_upper_php,
                    scenario.severe_loss_probability, scenario.expected_utility,
                    _json(scenario.utility_components), _json(scenario.feasibility_reasons),
                    _json(scenario.assumptions), scenario.created_at.isoformat(),
                ),
            )


def _decode_plan(conn, row) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    for key in ("cell_contexts_json", "summary_json", "warnings_json", "provenance_json"):
        item[key.removesuffix("_json")] = json.loads(item.pop(key))
    actions = []
    for action_row in conn.execute(
        "SELECT * FROM rehabilitation_actions_v3 WHERE plan_id = ? ORDER BY priority DESC, scheduled_date, id",
        (item["plan_id"],),
    ).fetchall():
        action = dict(action_row)
        for key in ("triggers_json", "evidence_ids_json", "instructions_json", "required_materials_json", "follow_up_dates_json"):
            action[key.removesuffix("_json")] = json.loads(action.pop(key))
        action["requires_field_confirmation"] = bool(action["requires_field_confirmation"])
        actions.append(action)
    scenarios = []
    for scenario_row in conn.execute(
        "SELECT * FROM rehabilitation_scenario_results WHERE plan_id = ? ORDER BY expected_utility DESC",
        (item["plan_id"],),
    ).fetchall():
        scenario = dict(scenario_row)
        for key in ("action_ids_json", "utility_components_json", "feasibility_reasons_json", "assumptions_json"):
            scenario[key.removesuffix("_json")] = json.loads(scenario.pop(key))
        scenarios.append(scenario)
    item["actions"] = actions
    item["scenarios"] = scenarios
    return item


def get_plan(plan_id: UUID | str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with connection(database_path) as conn:
        row = conn.execute(
            """SELECT id AS plan_id, farm_id, production_forecast_id, posterior_id,
                      pest_assessment_run_id, intercropping_run_id, planned_at,
                      cell_contexts_json, total_budget_php, available_labor_person_days,
                      planning_horizon_months, annual_discount_rate, risk_aversion,
                      farm_data_version, parameter_version, cost_catalog_version,
                      linked_weather_run_id, selected_scenario, total_expected_cost_php,
                      unallocated_budget_php, summary_json, warnings_json, data_notice,
                      provenance_json, created_at
               FROM rehabilitation_plan_runs WHERE id = ?""",
            (str(plan_id),),
        ).fetchone()
        return _decode_plan(conn, row)


def list_plans(
    *, farm_id: UUID | None = None, limit: int = 100,
    database_path: Path | None = None,
) -> list[dict[str, Any]]:
    where = "WHERE farm_id = ?" if farm_id else ""
    params = (str(farm_id), limit) if farm_id else (limit,)
    with connection(database_path) as conn:
        rows = conn.execute(
            f"""SELECT id AS plan_id, farm_id, production_forecast_id, posterior_id,
                       pest_assessment_run_id, intercropping_run_id, planned_at,
                       selected_scenario, total_expected_cost_php, total_budget_php,
                       unallocated_budget_php, parameter_version, created_at
                FROM rehabilitation_plan_runs {where}
                ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def summary(*, database_path: Path | None = None) -> dict[str, int]:
    tables = ("rehabilitation_plan_runs", "rehabilitation_actions_v3", "rehabilitation_scenario_results")
    with connection(database_path) as conn:
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
