# COCOAID Phase 11.3.13 — Farm Intelligence Runtime Fix

## Root cause fixed
The Phase 11.3.12 UI intentionally removed the visible Bayesian evidence and Suitability evidence cards, but `renderHealth()` still wrote to the removed DOM IDs `pestProbabilityBar`, `pestEvidenceList`, and `suitabilityFactors`. This caused a null-element JavaScript exception after a successful Analyze Farm Health request and stopped the remainder of Farm Intelligence from rendering.

## Corrections
- Removed hard dependency on the deleted health-evidence DOM mounts.
- Optional legacy render hooks now execute only when their DOM element exists.
- Isolated the pest-specific risk request so it cannot block core Farm Health rendering.
- Kept rehabilitation map, event calendar, health donuts, health charts, and CoCO-PILOT rehabilitation planner in the core render path.
- Bumped interface version to `phase11-agritech-interface-1.3.13` and static cache version to `11.3.13`.

## Verification
- `node --check app/static/app.js` — PASS
- Python compile checks for interface/workflow/verifier scripts — PASS
- Phase 11-focused unit tests — 86 PASS
- Phase 11.3.13 runtime regression tests — PASS
- Phase 11 verifier — PASS
- General installation verifier — PASS
- Direct TestClient health API checks:
  - `/api/pest-risk/evaluate` — HTTP 200
  - `/api/suitability/evaluate` — HTTP 200
  - `/api/farm-assessment` — HTTP 200
  - `/api/rehabilitation-plan` — HTTP 200; valid rehabilitation plan returned
  - `/api/pest-risk/specific` — HTTP 200; pest assessments returned

## Environment note
The verification sandbox currently has scikit-learn 1.8.0 while the archived models expect 1.9.0. The project requirements continue to specify the intended runtime version.
