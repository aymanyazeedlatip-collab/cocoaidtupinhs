# COCOAID Phase 11.3.14 Test Report

## Release scope
- Synchronized Selected Threat snapshot with the same Long-Term Model Forecast rain renderer and forecast-frame data.
- Event-conditioned Bayesian pest-pressure display and event-conditioned land suitability.
- Square rehabilitation grid clipped to the farm polygon.
- Interactive Decision-support Network, Reports, Database, and Methodology workspaces.
- Automatic Phase 9 -> Phase 10 background workflow without pasted UUIDs.
- CoCO-PILOT translucent holographic sphere with waiting, typing, loading, and speaking states.

## Automated test inventory
- Unit tests: 293 passed.
- Integration tests: 54 passed.
- Mathematical tests: 9 passed.
- Total: 356 passed.

## Verification scripts
- `scripts/verify_installation.py`: passed.
- `scripts/verify_phase9.py`: passed.
- `scripts/verify_phase10.py`: passed.
- `scripts/verify_phase11.py`: passed.
- Interface version: `phase11-agritech-interface-1.3.14`.

## Frontend integrity
- JavaScript syntax: passed (`node --check app/static/app.js`).
- Python compilation for new workflow runner, launcher, API route, and workflow scripts: passed.
- Duplicate HTML IDs: 0.
- Unresolved `$()` DOM references: 0.
- Phase 11 CSS parser errors: 0.
- Phase 11 asset checksum verifier: passed.

## Event-response checks
- Wet Bayesian test input produced higher posterior probability than dry input.
- Normal suitability example: 92.13%.
- Severe dry/heat suitability example: 65.60%.
- Selected Threat snapshot uses `drawRainDataUrl(frame)`, the same rain renderer used by Long-Term Model Forecast.
- Representative frame selection uses peak rainfall for rain events, peak temperature for heat stress, peak wind for typhoon, and the driest frame for drought.

## Automatic Phase 9 / Phase 10 end-to-end test
An isolated temporary SQLite database was seeded with an eligible v3 production forecast. COCOAID was launched through `launcher.py`, allowing the normal background workflow loop to operate.

Result:
- Phase 9: Complete.
- Phase 10: Complete.
- Pest assessment endpoint: 200.
- Intercropping assessment endpoint: 200.
- Rehabilitation plan endpoint: 200.
- Decision-support compose endpoint: 200.
- CoCO-PILOT deterministic narrative endpoint: 200.
- DOCX formal report generation/download: 200.
- PDF formal report generation/download: 200.
- No UUID was pasted manually.

## Runtime smoke test
Fresh launcher runtime returned HTTP 200 for:
- `/`
- `/api/health`
- `/api/v2/interface/status`
- `/api/v2/workflows/auto-phase9-10/status`
- `/weather-viewer`
- `/static/phase11.css`
- `/static/app.js`

## Environment note
The audit container has scikit-learn 1.8.0 while the project pins scikit-learn 1.9.0. The model registry therefore reports compatibility mode in this environment. The included project requirements retain the intended 1.9.0 runtime.
