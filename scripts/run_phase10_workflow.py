from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "manual_test_outputs"


def _uuid(value: str, label: str) -> str:
    cleaned = value.strip().strip('"').strip("'")
    try:
        return str(UUID(cleaned))
    except ValueError as exc:
        raise SystemExit(f"{label} is not a valid UUID: {cleaned}") from exc


def _json_request(client: httpx.Client, method: str, path: str, payload: dict | None = None) -> dict:
    try:
        response = client.request(method, path, json=payload)
    except httpx.ConnectError as exc:
        raise SystemExit("Could not connect to COCOAID. Start run.bat and leave it open.") from exc
    except httpx.HTTPError as exc:
        raise SystemExit(f"HTTP request failed: {type(exc).__name__}: {exc}") from exc
    if response.status_code >= 400:
        try:
            detail = json.dumps(response.json(), indent=2, ensure_ascii=False)
        except ValueError:
            detail = response.text
        raise SystemExit(f"{method} {path} failed with HTTP {response.status_code}:\n{detail}")
    return response.json()


def _latest_analysis_run_id(client: httpx.Client) -> str:
    listing = _json_request(client, "GET", "/api/v2/decision-support/runs?limit=1")
    items = listing.get("runs", [])
    if not items:
        raise SystemExit("No decision-support run was found. Run the Phase 9 workflow or compose a decision-support record first.")
    latest = items[0]
    return _uuid(str(latest["analysis_run_id"]), "Decision-support run ID")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 10 CoCO-PILOT and formal-report verification.")
    parser.add_argument("--analysis-run-id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    now = datetime.now().astimezone()
    output: dict[str, object] = {"started_at": now.isoformat()}

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180.0) as client:
        analysis_run_id = _uuid(args.analysis_run_id, "Decision-support run ID") if args.analysis_run_id else _latest_analysis_run_id(client)
        print(f"Using decision-support run ID: {analysis_run_id}")
        output["analysis_run_id"] = analysis_run_id
        print("\n[1/6] Verifying the Phase 9 decision-support record...")
        decision = _json_request(client, "GET", f"/api/v2/decision-support/runs/{analysis_run_id}")
        output["decision_support_record"] = decision
        print(f"      Status: {decision['status']}; recommendations: {len(decision.get('recommendations', []))}")

        print("[2/6] Generating a deterministic grounded CoCO-PILOT narrative...")
        narrative_request = {
            "analysis_run_id": analysis_run_id,
            "mode": "report_narrative",
            "question": "Summarize the integrated farm decision record for a formal report.",
            "provider_mode": "deterministic",
            "include_pca_references": True,
            "generated_at": now.isoformat(),
        }
        narrative = _json_request(client, "POST", "/api/v2/coco-pilot/explain", narrative_request)
        narrative_run_id = _uuid(narrative["run_id"], "CoCO-PILOT run ID")
        redaction = narrative.get("redaction_summary", {})
        if redaction.get("farmer_names_included") or redaction.get("raw_farmer_records_included"):
            raise SystemExit("Privacy verification failed: protected farmer data was included")
        if not narrative.get("citations"):
            raise SystemExit("Grounding verification failed: no citations were produced")
        output["narrative_request"] = narrative_request
        output["narrative_response"] = narrative
        print(f"      Narrative passed. Run ID: {narrative_run_id}")

        report_ids: dict[str, str] = {}
        for step, report_format in ((3, "docx"), (4, "pdf")):
            print(f"[{step}/6] Generating and downloading the {report_format.upper()} formal report...")
            report_request = {
                "analysis_run_id": analysis_run_id,
                "narrative_run_id": narrative_run_id,
                "report_format": report_format,
                "generated_at": now.isoformat(),
            }
            report = _json_request(client, "POST", "/api/v2/formal-reports/generate", report_request)
            report_id = _uuid(report["report_id"], f"{report_format.upper()} report ID")
            download = client.get(report["download_url"])
            if download.status_code != 200 or len(download.content) < 1000:
                raise SystemExit(f"{report_format.upper()} download failed or returned an incomplete file")
            if report_format == "docx" and not download.content.startswith(b"PK"):
                raise SystemExit("DOCX file signature verification failed")
            if report_format == "pdf" and not download.content.startswith(b"%PDF"):
                raise SystemExit("PDF file signature verification failed")
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            artifact_path = OUTPUT_DIR / report["filename"]
            artifact_path.write_bytes(download.content)
            report_ids[report_format] = report_id
            output[f"{report_format}_report_request"] = report_request
            output[f"{report_format}_report"] = report
            output[f"{report_format}_download_path"] = str(artifact_path)
            print(f"      {report_format.upper()} passed. Report ID: {report_id}")

        print("[5/6] Verifying stored assistant and report records...")
        stored_narrative = _json_request(client, "GET", f"/api/v2/coco-pilot/runs/{narrative_run_id}")
        stored_docx = _json_request(client, "GET", f"/api/v2/formal-reports/{report_ids['docx']}")
        stored_pdf = _json_request(client, "GET", f"/api/v2/formal-reports/{report_ids['pdf']}")
        output["stored_narrative"] = stored_narrative
        output["stored_docx"] = stored_docx
        output["stored_pdf"] = stored_pdf
        if "filepath" in stored_docx or "filepath" in stored_pdf:
            raise SystemExit("Privacy verification failed: internal report path was exposed")
        print("      Persistence verification passed.")

        print("[6/6] Verifying Phase 10 listings and safety status...")
        status = _json_request(client, "GET", "/api/v2/coco-pilot/status")
        reports = _json_request(client, "GET", f"/api/v2/formal-reports?analysis_run_id={analysis_run_id}&limit=10")
        runs = _json_request(client, "GET", f"/api/v2/coco-pilot/runs?analysis_run_id={analysis_run_id}&limit=10")
        if status["safety_policy"]["numeric_tables_generated_by_llm"] is not False:
            raise SystemExit("Safety status is incorrect")
        if reports.get("count", 0) < 2 or runs.get("count", 0) < 1:
            raise SystemExit("Phase 10 listing verification failed")
        output["phase10_status"] = status
        output["report_listing"] = reports
        output["narrative_listing"] = runs
        print("      Listings and safety policy passed.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    output_path = OUTPUT_DIR / f"phase10-workflow-{timestamp}.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nPHASE 10 MANUAL WORKFLOW PASSED")
    print(f"CoCO-PILOT run ID: {narrative_run_id}")
    print(f"DOCX report ID:    {report_ids['docx']}")
    print(f"PDF report ID:     {report_ids['pdf']}")
    print(f"Detailed results:  {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130)
