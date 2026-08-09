# COCOAID Phase 11.3.7 Test Report

## Automated test inventory
- Unit tests: 260 passed
- Integration tests: 54 passed
- Mathematical tests: 9 passed
- Total: 323 passed

## Focused Phase 11.3.7 verification
- Hourly provider-frame generation: PASS
- Weather GIS hourly playback parity: PASS
- Interactive forecast calendar structure: PASS
- Forecast panels closed by default: PASS
- Side-panel / Timeline mutual exclusion: PASS
- Weather GIS-style forecast wind implementation checks: PASS
- Phase 11.3.7 cache/version consistency: PASS

## Browser geometry / overlap audit
A headless Chromium layout audit used the real COCOAID HTML and production stylesheets at three representative viewport sizes:
- Desktop: 1440 × 900 — PASS
- Tablet: 1024 × 768 — PASS
- Mobile: 390 × 844 — PASS

The audit verified:
- `forecastMap` spans the full viewport width and height (within sub-pixel browser rounding).
- Menu/title, title/Refresh Forecast, Refresh/tool rail, tool rail/Timeline, title/Timeline, and all side-drawer/Timeline combinations do not intersect.
- Summary, Layers, and Graphs each occupy a collision-safe drawer lane.
- Dense open-calendar layout does not intersect the title, Refresh Forecast action, or tool rail.
- Calendar date labels do not overlap their provider/model status dots.

## Static and release verification
- `scripts/verify_phase11.py`: PASS
- `scripts/verify_installation.py`: PASS
- JavaScript syntax: PASS (`app.js`, `phase11.js`, Weather GIS `app.js`)
- Python compilation (`app`, `scripts`): PASS
- CSS parser audit: PASS, zero parser errors across main and Weather GIS stylesheets
- Duplicate DOM-ID audit: PASS, zero duplicate IDs
- Phase 11 asset manifests/checksums regenerated for interface version 1.3.7

## Runtime smoke verification
A fresh Uvicorn process returned HTTP 200 for:
- `/`
- `/api/health`
- `/api/v2/interface/status`
- `/static/phase11.css?v=11.3.7`
- `/static/app.js?v=11.3.7`
- `/weather-viewer`

## Environment note
The verification container has scikit-learn 1.8.0 while the project pins scikit-learn 1.9.0 for exact serialized-model reproducibility. The application therefore reports legacy compatibility mode in this sandbox. This is unrelated to the frontend change; the included project requirements retain the intended 1.9.0 runtime pin.
