from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.domain.intercropping import IntercropAssessmentRequest
from app.domain.pest import PestAssessmentRequest
from app.domain.rehabilitation import RehabilitationPlanRequest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from phase8_resume_payloads import (  # noqa: E402
    DEFAULT_CELL_ID,
    intercropping_payload,
    pest_assessment_payload,
    rehabilitation_payload,
)


def test_resume_payloads_are_contract_valid_and_json_serializable():
    now = datetime(2026, 8, 4, 3, 30, tzinfo=UTC)
    farm_id = str(uuid4())
    forecast_id = str(uuid4())
    observation_id = str(uuid4())
    pest_run_id = str(uuid4())
    intercrop_run_id = str(uuid4())

    pest = PestAssessmentRequest.model_validate(
        pest_assessment_payload(
            farm_id=farm_id,
            production_forecast_id=forecast_id,
            observation_id=observation_id,
            assessed_at=now,
        )
    )
    intercrop = IntercropAssessmentRequest.model_validate(
        intercropping_payload(
            farm_id=farm_id,
            production_forecast_id=forecast_id,
            pest_assessment_run_id=pest_run_id,
            assessed_at=now,
        )
    )
    rehabilitation = RehabilitationPlanRequest.model_validate(
        rehabilitation_payload(
            farm_id=farm_id,
            production_forecast_id=forecast_id,
            pest_assessment_run_id=pest_run_id,
            intercropping_run_id=intercrop_run_id,
            planned_at=now,
        )
    )

    assert str(pest.cell_id) == DEFAULT_CELL_ID
    assert len(pest.pest_profile_ids) == 5
    assert len(intercrop.candidate_ids) == 4
    assert rehabilitation.total_budget_php == 150000
    assert rehabilitation.available_labor_person_days == 100


def test_resume_payloads_preserve_phase8_manual_workflow_ids():
    now = datetime(2026, 8, 4, 3, 30, tzinfo=UTC)
    farm_id = str(uuid4())
    forecast_id = str(uuid4())
    observation_id = str(uuid4())
    pest_run_id = str(uuid4())
    intercrop_run_id = str(uuid4())

    pest = pest_assessment_payload(
        farm_id=farm_id,
        production_forecast_id=forecast_id,
        observation_id=observation_id,
        assessed_at=now,
    )
    intercrop = intercropping_payload(
        farm_id=farm_id,
        production_forecast_id=forecast_id,
        pest_assessment_run_id=pest_run_id,
        assessed_at=now,
    )
    rehabilitation = rehabilitation_payload(
        farm_id=farm_id,
        production_forecast_id=forecast_id,
        pest_assessment_run_id=pest_run_id,
        intercropping_run_id=intercrop_run_id,
        planned_at=now,
    )

    assert pest["production_forecast_id"] == forecast_id
    assert pest["observation_ids"] == [observation_id]
    assert intercrop["pest_assessment_run_id"] == pest_run_id
    assert rehabilitation["pest_assessment_run_id"] == pest_run_id
    assert rehabilitation["intercropping_run_id"] == intercrop_run_id
