from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coco_pilot import repository
from app.coco_pilot.reports import FORMAL_REPORT_GENERATOR_VERSION, generate_formal_report
from app.coco_pilot.service import (
    COCO_PILOT_ENGINE_VERSION, COCO_PILOT_PARAMETER_VERSION,
    COCO_PILOT_PROMPT_VERSION, CocoPilotService,
)
from app.core.config import settings
from app.domain.coco_pilot import CocoPilotRequest, FormalReportRequest
from app.engines.decision_support import DecisionSupportEngine
from app.storage.migrations import MigrationManager
from tests.phase9_factory import decision_request, prepare_phase9_records

REQUIRED_ARTIFACTS = [
    "docs/phase_10/ARCHITECTURE.md",
    "docs/phase_10/DATA_CONTRACTS.md",
    "docs/phase_10/GROUNDING_AND_SAFETY.md",
    "docs/phase_10/FORMAL_REPORTS.md",
    "docs/phase_10/DATABASE_SCHEMA.md",
    "docs/phase_10/API.md",
    "docs/phase_10/LIMITATIONS.md",
    "docs/phase_10/USER_ACTIONS.md",
    "docs/phase_10/PHASE_10_STATUS.md",
    "docs/phase_10/TEST_REPORT.md",
    "docs/phase_10/RELEASE_NOTES.md",
    "manifests/phase10_contract_hashes.json",
    "manifests/phase10_service_catalog.json",
    "manifests/phase10_endpoint_catalog.json",
    "manifests/phase10_migration_catalog.json",
    "run_phase10_workflow.bat",
    "scripts/run_phase10_workflow.py",
    "baseline_snapshots/phase10_test_results.txt",
]


def main() -> int:
    for relative in REQUIRED_ARTIFACTS:
        assert (ROOT / relative).exists(), f"Missing Phase 10 artifact: {relative}"
    assert settings.contract_api_version == "3.0.0-draft.10"
    assert COCO_PILOT_ENGINE_VERSION == "1.0.0"
    assert COCO_PILOT_PARAMETER_VERSION == "coco-pilot-grounding-parameters-1.0.0"
    assert COCO_PILOT_PROMPT_VERSION == "coco-pilot-structured-prompt-1.0.0"
    assert FORMAL_REPORT_GENERATOR_VERSION == "formal-report-generator-1.1.0"

    original_reports = settings.reports_dir
    try:
        with tempfile.TemporaryDirectory(prefix="cocoaid-phase10-") as temp:
            folder = Path(temp)
            database = folder / "phase10.sqlite3"
            settings.reports_dir = folder / "reports"
            manager = MigrationManager(database)
            assert manager.upgrade(target_version=10) == list(range(1, 11))
            assert manager.upgrade(target_version=10) == []
            production, posterior, pest, intercrop, rehabilitation = prepare_phase9_records(database_path=database)
            decision = DecisionSupportEngine(database_path=database).execute(
                decision_request(production, posterior, pest, intercrop, rehabilitation)
            ).output
            narrative = asyncio.run(CocoPilotService().explain(CocoPilotRequest(
                analysis_run_id=decision.record.analysis_run_id,
                mode="report_narrative",
                provider_mode="deterministic",
                include_pca_references=True,
                generated_at=datetime(2026, 8, 4, 6, tzinfo=UTC),
            ), database_path=database))
            assert narrative.provider == "deterministic"
            assert narrative.citations
            assert narrative.redaction_summary.farmer_names_included is False
            assert narrative.redaction_summary.raw_farmer_records_included is False
            assert repository.get_response(narrative.run_id, database_path=database)

            report_records = []
            for report_format in ("docx", "pdf"):
                record, path = generate_formal_report(FormalReportRequest(
                    analysis_run_id=decision.record.analysis_run_id,
                    narrative_run_id=narrative.run_id,
                    report_format=report_format,
                    generated_at=datetime(2026, 8, 4, 7, tzinfo=UTC),
                ), database_path=database)
                assert path.exists() and path.stat().st_size > 1000
                assert len(record.file_sha256) == 64 and len(record.content_fingerprint) == 64
                report_records.append(record)
                if report_format == "docx":
                    document = Document(BytesIO(path.read_bytes()))
                    text = "\n".join(item.text for item in document.paragraphs)
                    assert "Integrated Decision-Support Report" in text
                    assert "Prioritized Recommendations" in text
                else:
                    reader = PdfReader(BytesIO(path.read_bytes()))
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                    assert "Evidence Traceability" in text
            assert len(repository.list_reports(analysis_run_id=decision.record.analysis_run_id, database_path=database)) == 2
            assert repository.summary(database_path=database) == {"coco_pilot_runs": 1, "formal_report_runs": 2}

            with closing(sqlite3.connect(database)) as conn:
                conn.execute("PRAGMA foreign_keys=ON")
                assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
                assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert manager.downgrade_one(allow_destructive=True) == 10
            with closing(sqlite3.connect(database)) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                assert "coco_pilot_runs" not in tables
                assert "decision_support_runs" in tables
            assert manager.upgrade(target_version=10) == [10]
    finally:
        settings.reports_dir = original_reports

    result = (ROOT / "baseline_snapshots" / "phase10_test_results.txt").read_text(encoding="utf-8")
    assert "259 tests" in result
    assert "84 test files" in result
    assert "failure" not in result.lower()
    print(json.dumps({
        "contract_api_version": settings.contract_api_version,
        "migration_versions": list(range(1, 11)),
        "service_id": "v3.coco_pilot",
        "service_version": COCO_PILOT_ENGINE_VERSION,
        "parameter_version": COCO_PILOT_PARAMETER_VERSION,
        "prompt_version": COCO_PILOT_PROMPT_VERSION,
        "report_generator_version": FORMAL_REPORT_GENERATOR_VERSION,
        "deterministic_grounding_verified": True,
        "redaction_verified": True,
        "docx_verified": True,
        "pdf_verified": True,
        "persistence_verified": True,
    }, indent=2))
    print("PHASE 10 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
