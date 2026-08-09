from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_malformed_json_reports_line_column_and_parser_message_without_echoing_body():
    malformed = (
        '{\n'
        '  "farm_id": "550e8400-e29b-41d4-a716-446655440000",\n'
        '  "production_forecast_id": "550e8400-e29b-41d4-a716-446655440001"\n'
        '  "posterior_id": null\n'
        '}'
    )
    response = client.post(
        "/api/v2/pests/assess",
        content=malformed,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert "Malformed JSON at line" in payload["detail"]
    diagnostic = payload["details"]["json_error"]
    assert diagnostic["line"] == 4
    assert diagnostic["column"] >= 3
    assert "delimiter" in diagnostic["parser_message"].lower()
    assert diagnostic["body_echoed"] is False
    assert payload["errors"][0]["field"] == "request_body"
    assert payload["errors"][0]["value"] is None
    assert malformed not in response.text


def test_normal_contract_validation_keeps_field_level_errors():
    response = client.post("/api/v2/pests/assess", json={})
    assert response.status_code == 422
    payload = response.json()
    assert "json_error" not in payload["details"]
    fields = {item["field"] for item in payload["errors"]}
    assert "farm_id" in fields
    assert "production_forecast_id" in fields


def test_phase8_resume_payloads_complete_the_remaining_api_workflow():
    import sys
    from datetime import UTC, datetime
    from pathlib import Path
    from uuid import UUID

    from app.domain.enums import EvidenceStatus
    from app.domain.pest import PestObservation
    from app.domain.units import UnitCode
    from app.pest import repository as pest_repository
    from tests.phase7_factory import prepare_phase7_production

    scripts = Path(__file__).resolve().parents[2] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from phase8_resume_payloads import (  # noqa: E402
        DEFAULT_CELL_ID,
        intercropping_payload,
        pest_assessment_payload,
        rehabilitation_payload,
    )

    production = prepare_phase7_production()
    cell_id = UUID(DEFAULT_CELL_ID)
    observation = PestObservation(
        farm_id=production.forecast.farm_id,
        cell_id=cell_id,
        production_forecast_id=production.forecast.production_forecast_id,
        pest_profile_id="coconut-scale-insect",
        factor_code="scale_colonies",
        evidence_status=EvidenceStatus.FIELD_CONFIRMED,
        observed_at=datetime(2026, 8, 4, 1, tzinfo=UTC),
        value=True,
        unit=UnitCode.FRACTION,
        prevalence_fraction=0.15,
        source_label="Phase 8.1 resume integration test",
    )
    observation_id, _ = pest_repository.save_observation(observation)
    now = datetime(2026, 8, 4, 2, tzinfo=UTC)

    pest_response = client.post(
        "/api/v2/pests/assess",
        json=pest_assessment_payload(
            farm_id=str(production.forecast.farm_id),
            production_forecast_id=str(production.forecast.production_forecast_id),
            observation_id=str(observation_id),
            assessed_at=now,
        ),
    )
    assert pest_response.status_code == 200, pest_response.text
    pest_output = pest_response.json()["output"]
    assert len(pest_output["assessments"]) == 5

    intercrop_response = client.post(
        "/api/v2/intercropping/assess",
        json=intercropping_payload(
            farm_id=str(production.forecast.farm_id),
            production_forecast_id=str(production.forecast.production_forecast_id),
            pest_assessment_run_id=pest_output["run_id"],
            assessed_at=now,
        ),
    )
    assert intercrop_response.status_code == 200, intercrop_response.text
    intercrop_output = intercrop_response.json()["output"]
    assert intercrop_output["summary"]["total_assessment_count"] == 4

    rehabilitation_response = client.post(
        "/api/v2/rehabilitation/plan",
        json=rehabilitation_payload(
            farm_id=str(production.forecast.farm_id),
            production_forecast_id=str(production.forecast.production_forecast_id),
            pest_assessment_run_id=pest_output["run_id"],
            intercropping_run_id=intercrop_output["run_id"],
            planned_at=now,
        ),
    )
    assert rehabilitation_response.status_code == 200, rehabilitation_response.text
    plan = rehabilitation_response.json()["output"]["plan"]
    assert len(plan["scenarios"]) == 6
    selected = next(
        item for item in plan["scenarios"]
        if item["scenario_type"] == plan["selected_scenario"]
    )
    assert selected["status"] == "feasible"
