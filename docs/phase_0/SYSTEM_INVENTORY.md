# Legacy System Inventory

## Baseline

- Product version: COCO-AID 2.11.0
- Backend: FastAPI and Pydantic
- Persistence: SQLite with JSON payload columns
- Frontend: static HTML, CSS, and vanilla JavaScript
- Analytical components: production, pest, suitability, climate projection, stochastic farm simulation, rehabilitation mapping, reports, and optional Gemini assistant
- Automated tests discovered: 111 test functions across 25 files
- API routes discovered: 59

## Largest text source files

| Path | Lines | Type |
| --- | --- | --- |
| data/official/psa_province_profiles.json | 51407 | .json |
| app/static/styles.css | 3464 | .css |
| app/static/app.js | 2808 | .js |
| app/static/weather-viewer/app.js | 2096 | .js |
| app/static/weather-viewer/styles.css | 1343 | .css |
| app/simulation/farm_site_forecast.py | 996 | .py |
| app/static/index.html | 976 | .html |
| app/simulation/engine.py | 541 | .py |
| app/reports/docx.py | 511 | .py |
| app/reports/pdf.py | 508 | .py |
| app/api/routes.py | 487 | .py |
| app/gis/analysis.py | 476 | .py |
| app/static/weather-viewer/index.html | 400 | .html |
| app/services/assistant.py | 365 | .py |
| app/weather/providers.py | 355 | .py |
| app/math/pest_specific.py | 337 | .py |
| app/storage/database.py | 263 | .py |
| CHANGELOG.md | 260 | .md |
| app/reports/visuals.py | 221 | .py |
| app/schemas/analysis.py | 209 | .py |

## Coupling observations

- `app/static/app.js` contains 2808 lines.
- `app/static/styles.css` contains 3464 lines.
- `app/api/routes.py` centralizes most HTTP orchestration.
- `app/simulation/farm_site_forecast.py` combines weather merging, long-range projection, product calculations, hazard generation, and spatial frame construction.
- The new engines must be introduced behind explicit service contracts rather than added to these monoliths.
