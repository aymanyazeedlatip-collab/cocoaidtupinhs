# COCOAID Phase 11.3.23 — Render Font Startup Hotfix

## Incident

Render Free/Linux startup failed during `bash scripts/start_production.sh` with:

`reportlab.pdfbase.ttfonts.TTFError: Can't open file "."`

## Root cause

`app/reports/pdf.py` used `Path()` as the fallback when no optional Times-compatible TTF file was found. `Path()` resolves to the current directory (`.`), and `Path('.').exists()` is true. The loader therefore passed a directory to ReportLab `TTFont`, causing the FastAPI process to terminate before Uvicorn could finish startup.

## Fix

- Replaced directory/placeholder existence checks with real-file checks (`Path.is_file()`).
- Removed `Path()` as a missing-font sentinel.
- Added guarded ReportLab registration in both PDF paths:
  - `app/reports/pdf.py`
  - `app/coco_pilot/reports.py`
- If Linux/Render does not provide a compatible Times/Tinos/DejaVu TTF family, COCOAID now falls back to ReportLab's built-in Times family.
- Optional system-font failure can no longer prevent application startup.
- No font files are bundled with this hotfix.

## Verification

- Directory-as-font regression reproduced and prevented.
- Production startup smoke test reached `Application startup complete`.
- `/api/health` returned HTTP 200.
- 348 unit tests passed.
- 54 integration tests passed.
- 9 mathematical tests passed.
- 411 automated tests passed total.
- Installation verification passed.
- Phase 9 verification passed.
- Phase 10 verification passed, including DOCX/PDF generation.
- Phase 11 verification passed.
- Zero-cost deployment verification passed.
