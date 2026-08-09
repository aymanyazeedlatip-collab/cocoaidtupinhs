from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import httpx

from phase8_resume_payloads import (
    intercropping_payload,
    pest_assessment_payload,
    rehabilitation_payload,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "manual_test_outputs"


def _uuid(value: str, label: str) -> str:
    cleaned = value.strip().strip('"').strip("'")
    try:
        return str(UUID(cleaned))
    except ValueError as exc:
        raise SystemExit(f"{label} is not a valid UUID: {cleaned}") from exc


def _request(client: httpx.Client, method: str, path: str, *, payload: dict | None = None) -> dict:
    try:
        response = client.request(method, path, json=payload)
    except httpx.ConnectError as exc:
        raise SystemExit(
            "Could not connect to COCOAID at http://127.0.0.1:8000. "
            "Start run.bat first, leave its terminal open, then run this script again."
        ) from exc
    except httpx.HTTPError as exc:
        raise SystemExit(f"HTTP request failed before a response was received: {type(exc).__name__}: {exc}") from exc

    if response.status_code >= 400:
        try:
            detail = json.dumps(response.json(), indent=2, ensure_ascii=False)
        except ValueError:
            detail = response.text
        raise SystemExit(f"{method} {path} failed with HTTP {response.status_code}:\n{detail}")
    return response.json()


def _prompt(value: str | None, label: str) -> str:
    return value or input(f"Paste {label}: ").strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resume the Phase 8 manual verification from the pest-assessment step without manually editing JSON."
        )
    )
    parser.add_argument("--production-forecast-id")
    parser.add_argument("--observation-id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    production_forecast_id = _uuid(
        _prompt(args.production_forecast_id, "output.forecast.production_forecast_id"),
        "Production forecast ID",
    )
    observation_id = _uuid(
        _prompt(args.observation_id, "observation_id"),
        "Observation ID",
    )

    now = datetime.now().astimezone()
    output: dict[str, object] = {
        "started_at": now.isoformat(),
        "production_forecast_id": production_forecast_id,
        "observation_id": observation_id,
    }

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120.0) as client:
        print("\n[1/5] Verifying the production forecast...")
        production = _request(client, "GET", f"/api/v2/production/forecasts/{production_forecast_id}")
        farm_id = _uuid(str(production["farm_id"]), "Farm ID from production forecast")
        output["production_forecast"] = production
        print(f"      Production forecast found for farm {farm_id}")

        print("[2/5] Running the five-profile pest assessment...")
        pest_request = pest_assessment_payload(
            farm_id=farm_id,
            production_forecast_id=production_forecast_id,
            observation_id=observation_id,
            assessed_at=now,
        )
        pest_response = _request(client, "POST", "/api/v2/pests/assess", payload=pest_request)
        pest_output = pest_response["output"]
        pest_run_id = _uuid(str(pest_output["run_id"]), "Pest assessment run ID")
        assessments = pest_output.get("assessments", [])
        if len(assessments) != 5:
            raise SystemExit(f"Expected 5 pest assessments but received {len(assessments)}")
        for item in assessments:
            if float(item["expected_loss"]) > float(item["conditional_loss"]) + 1e-9:
                raise SystemExit("Pest loss validation failed: expected loss exceeds conditional loss")
        output["pest_request"] = pest_request
        output["pest_response"] = pest_response
        print(f"      Pest assessment passed. Run ID: {pest_run_id}")

        print("[3/5] Running the intercropping assessment...")
        intercrop_request = intercropping_payload(
            farm_id=farm_id,
            production_forecast_id=production_forecast_id,
            pest_assessment_run_id=pest_run_id,
            assessed_at=now,
        )
        intercrop_response = _request(
            client, "POST", "/api/v2/intercropping/assess", payload=intercrop_request
        )
        intercrop_output = intercrop_response["output"]
        intercropping_run_id = _uuid(str(intercrop_output["run_id"]), "Intercropping run ID")
        if int(intercrop_output["summary"]["total_assessment_count"]) != 4:
            raise SystemExit("Expected 4 intercropping assessments")
        output["intercropping_request"] = intercrop_request
        output["intercropping_response"] = intercrop_response
        print(f"      Intercropping assessment passed. Run ID: {intercropping_run_id}")

        print("[4/5] Generating the rehabilitation plan...")
        rehab_request = rehabilitation_payload(
            farm_id=farm_id,
            production_forecast_id=production_forecast_id,
            pest_assessment_run_id=pest_run_id,
            intercropping_run_id=intercropping_run_id,
            planned_at=now,
        )
        rehab_response = _request(client, "POST", "/api/v2/rehabilitation/plan", payload=rehab_request)
        plan = rehab_response["output"]["plan"]
        plan_id = _uuid(str(plan["rehabilitation_plan_id"]), "Rehabilitation plan ID")
        scenarios = plan.get("scenarios", [])
        if len(scenarios) != 6:
            raise SystemExit(f"Expected 6 scenarios but received {len(scenarios)}")
        no_action = next((item for item in scenarios if item.get("scenario_type") == "no_action"), None)
        if not no_action or no_action.get("status") != "feasible" or float(no_action.get("total_cost_php", -1)) != 0:
            raise SystemExit("Mandatory no-action scenario validation failed")
        selected_type = str(plan["selected_scenario"])
        selected = next(
            (item for item in scenarios if item.get("scenario_type") == selected_type),
            None,
        )
        if not selected or selected.get("status") != "feasible":
            raise SystemExit("Selected rehabilitation scenario is not feasible or could not be resolved")
        output["rehabilitation_request"] = rehab_request
        output["rehabilitation_response"] = rehab_response
        print(f"      Rehabilitation plan passed. Plan ID: {plan_id}")

        print("[5/5] Verifying saved-plan retrieval...")
        saved_plan = _request(client, "GET", f"/api/v2/rehabilitation/plans/{plan_id}")
        output["saved_plan"] = saved_plan
        print("      Saved-plan retrieval passed.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    output_path = OUTPUT_DIR / f"phase8-resume-{timestamp}.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nPHASE 8 MANUAL WORKFLOW PASSED")
    print(f"Pest assessment run ID: {pest_run_id}")
    print(f"Intercropping run ID:   {intercropping_run_id}")
    print(f"Rehabilitation plan ID: {plan_id}")
    print(f"Detailed results saved to: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130)
