from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from app.core.error_handlers import _json_position
from app.domain.intercropping import IntercropAssessmentRequest
from app.domain.pest import PestAssessmentRequest
from app.domain.rehabilitation import RehabilitationPlanRequest
from phase8_resume_payloads import intercropping_payload, pest_assessment_payload, rehabilitation_payload


def main() -> int:
    required = [
        ROOT / "resume_phase8_workflow.bat",
        ROOT / "scripts" / "resume_phase8_workflow.py",
        ROOT / "scripts" / "phase8_resume_payloads.py",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing Phase 8.1 workflow files: {missing}")

    line, column = _json_position('{\n  "x": 1\n  "y": 2\n}', 13)
    if line < 2 or column < 1:
        raise RuntimeError("JSON position diagnostics are not working")

    now = datetime(2026, 8, 4, tzinfo=UTC)
    farm = str(uuid4())
    forecast = str(uuid4())
    observation = str(uuid4())
    pest_run = str(uuid4())
    intercrop_run = str(uuid4())
    PestAssessmentRequest.model_validate(pest_assessment_payload(
        farm_id=farm,
        production_forecast_id=forecast,
        observation_id=observation,
        assessed_at=now,
    ))
    IntercropAssessmentRequest.model_validate(intercropping_payload(
        farm_id=farm,
        production_forecast_id=forecast,
        pest_assessment_run_id=pest_run,
        assessed_at=now,
    ))
    RehabilitationPlanRequest.model_validate(rehabilitation_payload(
        farm_id=farm,
        production_forecast_id=forecast,
        pest_assessment_run_id=pest_run,
        intercropping_run_id=intercrop_run,
        planned_at=now,
    ))
    print("PHASE 8.1 JSON WORKFLOW VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
