from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import httpx

from phase8_resume_payloads import intercropping_payload, pest_assessment_payload, rehabilitation_payload

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
        raise SystemExit(f"HTTP request failed: {type(exc).__name__}: {exc}") from exc
    if response.status_code >= 400:
        try:
            detail = json.dumps(response.json(), indent=2, ensure_ascii=False)
        except ValueError:
            detail = response.text
        raise SystemExit(f"{method} {path} failed with HTTP {response.status_code}:\n{detail}")
    return response.json()



def _latest_forecast_and_observation(client: httpx.Client) -> tuple[str, str | None]:
    forecasts = _request(client, "GET", "/api/v2/production/forecasts?limit=1")
    items = forecasts.get("forecasts", [])
    if not items:
        raise SystemExit("No production forecast was found. Run a farm forecast in the app first.")
    latest_forecast = items[0]
    farm_id = _uuid(str(latest_forecast["farm_id"]), "Farm ID")
    observations = _request(client, "GET", f"/api/v2/pests/observations?farm_id={farm_id}&limit=1")
    obs = observations.get("observations", [])
    observation_id = _uuid(str(obs[0]["id"]), "Pest observation ID") if obs else None
    return _uuid(str(latest_forecast["id"]), "Production forecast ID"), observation_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 9 integrated decision-support verification without editing JSON manually.")
    parser.add_argument("--production-forecast-id")
    parser.add_argument("--observation-id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--all-intercrops", action="store_true", help="Assess the complete intercrop candidate catalog instead of the four workflow smoke-test candidates.")
    args = parser.parse_args()

    now = datetime.now().astimezone()
    output: dict[str, object] = {"started_at": now.isoformat()}

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180.0) as client:
        if args.production_forecast_id:
            production_forecast_id = _uuid(args.production_forecast_id, "Production forecast ID")
            production = _request(client, "GET", f"/api/v2/production/forecasts/{production_forecast_id}")
            farm_id_for_obs = _uuid(str(production["farm_id"]), "Farm ID")
            if args.observation_id:
                observation_id = _uuid(args.observation_id, "Pest observation ID")
            else:
                obs_rows = _request(client, "GET", f"/api/v2/pests/observations?farm_id={farm_id_for_obs}&limit=1").get("observations", [])
                observation_id = _uuid(str(obs_rows[0]["id"]), "Pest observation ID") if obs_rows else None
        else:
            production_forecast_id, observation_id = _latest_forecast_and_observation(client)
        print(f"Auto-selected forecast: {production_forecast_id}")
        print(f"Pest observation: {observation_id or 'none (context-only assessment)'}")
        output["production_forecast_id"] = production_forecast_id
        output["observation_id"] = observation_id
        print("\n[1/7] Verifying the production forecast...")
        production = _request(client, "GET", f"/api/v2/production/forecasts/{production_forecast_id}")
        farm_id = _uuid(str(production["farm_id"]), "Farm ID")
        cell_id = str(production.get("cell_id") or "11111111-1111-4111-8111-111111111111")
        output["production_forecast"] = production
        print(f"      Production forecast found for farm {farm_id}")

        print("[2/7] Running the five-profile pest assessment...")
        pest_request = pest_assessment_payload(farm_id=farm_id, production_forecast_id=production_forecast_id, observation_id=observation_id, assessed_at=now, cell_id=cell_id)
        pest_response = _request(client, "POST", "/api/v2/pests/assess", payload=pest_request)
        pest_run_id = _uuid(str(pest_response["output"]["run_id"]), "Pest assessment run ID")
        if len(pest_response["output"].get("assessments", [])) != 5:
            raise SystemExit("Expected five pest assessments")
        output["pest_request"] = pest_request
        output["pest_response"] = pest_response
        print(f"      Pest assessment passed. Run ID: {pest_run_id}")

        print("[3/7] Running the intercropping assessment...")
        intercrop_request = intercropping_payload(farm_id=farm_id, production_forecast_id=production_forecast_id, pest_assessment_run_id=pest_run_id, assessed_at=now, cell_id=cell_id)
        if args.all_intercrops:
            intercrop_request["candidate_ids"] = []
        intercrop_response = _request(client, "POST", "/api/v2/intercropping/assess", payload=intercrop_request)
        intercrop_run_id = _uuid(str(intercrop_response["output"]["run_id"]), "Intercropping run ID")
        assessment_count = int(intercrop_response["output"]["summary"]["total_assessment_count"])
        if args.all_intercrops and assessment_count < 30:
            raise SystemExit(f"Expected the complete intercrop catalog, received only {assessment_count} assessments")
        if not args.all_intercrops and assessment_count != 4:
            raise SystemExit("Expected four intercropping assessments")
        output["intercropping_request"] = intercrop_request
        output["intercropping_response"] = intercrop_response
        print(f"      Intercropping assessment passed. Run ID: {intercrop_run_id}")

        print("[4/7] Generating the rehabilitation plan...")
        rehab_request = rehabilitation_payload(farm_id=farm_id, production_forecast_id=production_forecast_id, pest_assessment_run_id=pest_run_id, intercropping_run_id=intercrop_run_id, planned_at=now, cell_id=cell_id)
        rehab_response = _request(client, "POST", "/api/v2/rehabilitation/plan", payload=rehab_request)
        plan = rehab_response["output"]["plan"]
        plan_id = _uuid(str(plan["rehabilitation_plan_id"]), "Rehabilitation plan ID")
        scenarios = plan.get("scenarios", [])
        if len(scenarios) != 6:
            raise SystemExit("Expected six rehabilitation scenarios")
        output["rehabilitation_request"] = rehab_request
        output["rehabilitation_response"] = rehab_response
        print(f"      Rehabilitation plan passed. Plan ID: {plan_id}")

        print("[5/7] Composing the integrated decision-support record...")
        decision_request = {
            "farm_id": farm_id,
            "production_forecast_id": production_forecast_id,
            "posterior_id": None,
            "pest_assessment_run_id": pest_run_id,
            "intercropping_run_id": intercrop_run_id,
            "rehabilitation_plan_id": plan_id,
            "generated_at": now.isoformat(),
            "requested_components": ["production", "pest", "intercropping", "rehabilitation"],
            "failure_policy": "continue_optional",
            "farm_data_version": "phase9-manual-test-farm-1"
        }
        decision_response = _request(client, "POST", "/api/v2/decision-support/compose", payload=decision_request)
        record = decision_response["output"]["record"]
        analysis_run_id = _uuid(str(record["analysis_run_id"]), "Analysis run ID")
        if record["status"] != "completed":
            raise SystemExit(f"Expected completed decision-support record, received {record['status']}")
        if float(record["overview"]["data_completeness"]) != 1.0:
            raise SystemExit("Expected 100% completeness for the four requested components")
        if not record.get("recommendations"):
            raise SystemExit("No decision recommendations were generated")
        output["decision_request"] = decision_request
        output["decision_response"] = decision_response
        print(f"      Decision-support record passed. Run ID: {analysis_run_id}")

        print("[6/7] Verifying saved decision-support retrieval...")
        saved = _request(client, "GET", f"/api/v2/decision-support/runs/{analysis_run_id}")
        if len(saved.get("component_results", [])) != 5:
            raise SystemExit("Saved decision-support record did not preserve all component status entries")
        output["saved_decision_support_record"] = saved
        print("      Saved-record retrieval passed.")

        print("[7/7] Verifying run listing...")
        listing = _request(client, "GET", f"/api/v2/decision-support/runs?farm_id={farm_id}&limit=10")
        if int(listing.get("count", 0)) < 1:
            raise SystemExit("Decision-support listing did not return the saved run")
        output["decision_support_listing"] = listing
        print("      Run listing passed.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    output_path = OUTPUT_DIR / f"phase9-workflow-{timestamp}.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nPHASE 9 MANUAL WORKFLOW PASSED")
    print(f"Pest assessment run ID:    {pest_run_id}")
    print(f"Intercropping run ID:      {intercrop_run_id}")
    print(f"Rehabilitation plan ID:    {plan_id}")
    print(f"Decision-support run ID:   {analysis_run_id}")
    print(f"Detailed results saved to: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130)
