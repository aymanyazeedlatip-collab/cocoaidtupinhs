# COCOAID Phase 11.3.9 Test Report

## Automated test inventory
- Unit: 276 passed
- Integration: 54 passed
- Mathematical: 9 passed
- Total: 339 passed

## Focused regression coverage
Phase 11.3.9 adds explicit checks for:
- visible NASA GIBS Satellite pane and base-map opacity restoration;
- Selected Threat event icon, interactive event map, and weather-detail mounts;
- separate calendar lanes for date numbers and event pings;
- orange/red Technical Comparison chart palette;
- exact Farm Health map centering using farm bounds;
- event-specific refresh of pest pressure, land suitability, and farm condition;
- interactive rehabilitation calendar phases;
- interface version and cache-busted static assets.

## Release verifiers
- `scripts/verify_phase11.py`: PASS
- `scripts/verify_installation.py`: PASS

## Static/runtime checks
- `node --check app/static/app.js`: PASS
- `node --check app/static/phase11.js`: PASS
- `python -m compileall -q app`: PASS
- CSS parse errors: 0
- Duplicate DOM IDs: 0
- `/`: HTTP 200
- `/api/health`: HTTP 200
- `/api/v2/interface/status`: HTTP 200
- `/static/phase11.css`: HTTP 200
- `/static/app.js`: HTTP 200
- `/weather-viewer`: HTTP 200

## Environment note
The verification container has scikit-learn 1.8.0 while the project requirements/model cards expect 1.9.0. The models therefore load in documented compatibility mode in this environment. The project requirements retain the intended 1.9.0 version.

## Browser-rendering note
The environment's Chromium policy blocks loopback navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`, so no unsupported claim of a live Chromium visual pass is made. UI behavior is guarded by focused DOM/CSS/JavaScript regression tests plus fresh HTTP/runtime checks.
