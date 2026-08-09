## Phase 11 official agri-tech interface

Phase 11 completes the presentation-layer rebuild. COCOAID now uses a fixed white institutional agri-tech theme, an interactive coconut hologram, dedicated Weather GIS and Decision Network pages, universal chart controls, and formal Times New Roman office reports. Music, voice lines, analytical engines, model artifacts, and migrations remain preserved.

Useful checks:

```powershell
python scripts\verify_phase11.py
python scripts\run_test_suite.py
```

## Phase 10 CoCO-PILOT and formal report generation

Phase 10 adds a privacy-filtered, source-grounded CoCO-PILOT service above the Phase 9 decision-support record. Deterministic explanations are always available; Google AI is optional and may only rewrite a validated deterministic draft. DOCX and PDF reports populate numeric tables directly from stored analytical fields and preserve checksums, content fingerprints, citations, and provenance. Use `run_phase10_workflow.bat` for the guided verification path.


## Phase 9 integrated decision-support network

Phase 9 adds `v3.decision_support`, which composes versioned production, Bayesian, pest, intercropping, and rehabilitation outputs into one reproducible decision record. Each recommendation preserves its source component, record identifier, evidence field, confidence, confirmation requirement, and limitations. Partial component availability is disclosed rather than hidden. Use `run_phase9_workflow.bat` for the guided verification path.

> **COCOAID v3 rehaul workspace:** Phases 0–11 are complete. The preserved v2.11 implementation remains active while the v3 data foundation, weather, production, Bayesian, pest, and intercropping engines coexist through versioned contracts. See [`PROJECT_INITIATION.md`](PROJECT_INITIATION.md) and [`docs/phase_7/PHASE_7_STATUS.md`](docs/phase_7/PHASE_7_STATUS.md).

# COCO-AID v2.11.0

**Bayesian Probabilistic Agroecosystem Simulation and Geospatial AI-Based Decision-Support Framework for Coconut Rehabilitation**

COCO-AID is a software-only research prototype combining official Philippine coconut-production statistics, farm GIS, short-term weather maps, climate-conditioned long-term simulation, Bayesian pest analysis, land suitability, rehabilitation prioritization, report generation, and the optional Gemini-powered **CoCO-PILOT** assistant.

## COCOAID v3 Phase 1 architecture

Phase 1 is additive and does not replace the current interface. It provides:

- strict farm, weather, production, Bayesian, pest, intercropping, rehabilitation, and provenance contracts;
- canonical units and explicit conversion rules;
- analytical engine, model, and parameter registries;
- checksummed SQLite migrations;
- structured errors, request IDs, and processing-time headers;
- read-only architecture endpoints under `/api/v2`;
- exact `scikit-learn==1.9.0` model-runtime pinning.

Useful local checks:

```powershell
python scripts\migrations.py status
python scripts\verify_phase1.py
```

Contract API documentation remains available in the normal FastAPI interface at `http://127.0.0.1:8000/docs`.

## COCOAID v3 Phase 2 data foundation

Phase 2 originally established the normalized reference foundation. The current registry contains 16 checksum-registered sources, 30 coconut varieties with 408 parameters, five PCA pest/disease profiles, 35 intercrop candidates, 81 canopy-light records, two fertilization scenarios, and an explicit privacy-separated importer for the 17,798-row farmer workbook. The farmer registry is not imported automatically.

Useful checks:

```powershell
python scripts\verify_phase2.py
python scripts\import_farmer_registry.py --dry-run
```

The Phase 1 Starlette warning is corrected by installing HTTPX2, and pytest now treats all warnings as failures.


## COCOAID v3 Phase 3 weather assimilation

Phase 3 adds migration 3, versioned weather runs and values, a 16-day live forecast boundary, `weather-features-1.0.0`, run comparison, cache/rate-limit disclosure, and an executable `v3.weather_assimilation` engine. Weather updates inputs and predictions; they do not retrain the preserved ML model.

Useful checks:

```powershell
python scripts\verify_phase3.py
python -m pytest -q
```

Weather status and assimilation are available under `/api/v2/weather/*`.

## COCOAID v3 Phase 4 production engine

Phase 4 adds migration 4 and the executable `v3.production` engine while preserving the retained model artifact unchanged. It introduces an exact 19-feature adapter, named PCA variety adjustments, product conversions, forecast persistence, v2.11 shadow comparison, and actual-versus-predicted monitoring. Bayesian posterior computation remains reserved for Phase 5.

The new PCA Region XII income workbook is registered as a restricted source. Only sanitized aggregate cacao and coffee economic profiles are exposed.

Useful checks:

```powershell
python scripts\verify_phase4.py
python -m pytest -p pytest_asyncio.plugin -q
```

Production status and forecasts are available under `/api/v2/production/*`.


## COCOAID v3 Phase 5 Bayesian farm-state simulator

Phase 5 adds migration 5 and the executable `v3.bayesian` engine. A seeded sequential importance/resampling particle filter propagates seven palm states, soil fertility, soil water, and production uncertainty. Real observations can update the posterior according to explicit reliability levels; predicted and suspected records remain traceability-only and never update particle weights.

Useful checks:

```powershell
python scripts\verify_phase5.py
python scripts\run_test_suite.py
```

Bayesian status, evidence, simulation, and stored posteriors are available under `/api/v2/bayesian/*`.

## COCOAID v3 Phase 6 pest-risk inference

Phase 6 adds migration 6 and `v3.pest_inference`. Five PCA-supported pest and disease profiles are evaluated independently using reliability-gated observations, versioned spatial pressure, separate conditional and expected loss, and source-linked management actions.

Useful checks:

```powershell
python scripts\verify_phase6.py
```

Pest profiles, observations, and assessments are available under `/api/v2/pests/*`.

## COCOAID v3 Phase 7 intercropping potential

Phase 7 adds migration 7 and `v3.intercropping`. It evaluates 35 crop candidates per farm cell using PCA canopy-light transmission, versioned crop requirements, nine decomposable suitability components, hard constraints, coconut competition, optional pest compatibility, and sanitized cacao/coffee gross-revenue scenarios. It is explicitly an evidence-based scoring engine, not a trained intercropping ML model.

Useful checks:

```powershell
python scripts\verify_phase7.py
python scripts\run_test_suite.py
```

Status, candidates, assessment creation, and stored results are available under `/api/v2/intercropping/*`.

## Scientific interpretation

Official Philippine Statistics Authority provincial production records are used where the bundled source supports them. Individual-farm conditions, missing periods, and future values remain model estimates. Long-term daily weather fields are plausible climate-conditioned projections, not exact forecasts of future clouds, typhoons, or rainfall dates.

## Fast Windows setup

1. Create a short writable folder such as `C:\COCOAID\P11` and extract the flat ZIP contents directly into it.
2. Double-click `setup.bat`. The installer stores its virtual environment under LocalAppData to avoid Windows long-path failures.
3. Wait for **COCO-AID verification passed** and **SETUP COMPLETE**.
4. Double-click `run.bat`.
5. Open `http://127.0.0.1:8000` if the browser does not open automatically.

Python 3.11 is the supported target. Internet access is needed for map tiles, live weather providers, externally hosted pest photography, and Gemini. Core assessment, long-term simulation, local storage, and reports remain available when those online services are unavailable.

## v2.11.0 navigation layout fix

- Corrects sidebar labels that could inherit the icon width and appear truncated.
- Adds a fluid 380 ms collapse/open transition for the sidebar, navigation labels, controls, and content column.
- Reflows the coconut-farm background while the navigation rail changes width so each tab remains fully covered.
- Recalculates map dimensions after the transition completes.


## v2.10.0 preview, sound, navigation, and settings update

- Reworked the pre-entry experience into a bright light-theme technology portal.
- Starts the bundled background soundtrack on the preview page whenever the browser permits autoplay; any preview interaction provides the required browser fallback.
- Keeps background music at a constant 10% level, including while voice guidance is playing.
- Added a persistent desktop control for collapsing and reopening the navigation sidebar without changing tab arrangement.
- Removed the sidebar logo subtext and removed Settings-specific voice narration.
- Fixed the Settings drawer so its contents scroll independently without moving the page behind it.

## v2.6.0 liquid-glass interface update

- Applied a layout-preserving liquid-glass visual layer across navigation, panels, cards, dialogs, controls, the loading screen, and the embedded Weather GIS.
- Added translucent refraction gradients, inner edge highlights, controlled blur, deeper floating surfaces, and dark smoked-glass equivalents.
- Kept maps, charts, tables, forms, tab order, and workflow placement unchanged.
- Added browser fallbacks for systems without backdrop-filter support and retained reduced-motion behavior.
- Repaired the Pest-specific outbreak section so the heading, empty state, score summary, and dynamic cards remain inside their boundaries at desktop and mobile widths.
- Added the supplied official Weather GIS and CoCO-PILOT artwork to floating buttons, the Weather GIS header/favicon, the Weather GIS modal, and the assistant header.

## v2.5.0 final visual identity update

- Integrated the supplied COCO-AID logo, stylized wordmark, and coconut-farm landing image.
- Added a saturated modern agri-tech visual system with restrained motion and richer chart colors.
- Added a branded loading experience with rotating logo, circular loader, progress animation, and rotating farm-planning tips.
- Added a complete About page crediting researcher Gavrielle Munoz and Tupi National High School.
- Preserved the v2.4.1 mathematical, weather, farm, assistant, reporting, and rehabilitation functionality.

## v2.4.1 rehabilitation and Gemini update

- Updated the default CoCO-PILOT model to `gemini-flash-latest` and added automatic fallback from retired model identifiers.
- Rebuilt rehabilitation planning around forecast extreme-weather events instead of one static farm-wide grid.
- Added one selectable rehabilitation heatmap for each projected typhoon, drought, extreme-rain, or heat-stress period.
- Added green, yellow, and red management classes: No Damage, Needs inspection, and Needs Rehabilitation.
- Added recommended field-inspection, rehabilitation, 30-day follow-up, and 90-day follow-up dates.
- Added event-specific rehabilitation procedures covering safety, field verification, drainage or moisture management, sanitation, integrated pest management, and recovery monitoring.
- Added a CoCO-PILOT rehabilitation work-plan generator that uses the selected event, farm, forecast, pest, suitability, and health context.
- Added event-linked rehabilitation schedules to PDF and DOCX report supplements.
- Added 85 automated tests, including Gemini model fallback, event-plan date calculation, multi-event heatmaps, and rehabilitation UI contracts.

## Main workflow

1. **Home** — review the landing page and live Weather GIS, draw a quick farm polygon, or open Farm Setup.
2. **Farm Setup** — enter farm identity, boundary, trees, production, soil, symptoms, and management data, then save the farm to SQLite.
3. **Farm Site Forecast** — generate a daily animated climate-conditioned outlook through 2050 linked to weekly agricultural production control points.
4. **Extreme Weather** — inspect projected typhoon exposure, drought, extreme-rain, and heat-stress periods with estimated farm effects.
5. **Farm Health** — review Bayesian pest risk, pest-specific assessments, suitability mathematics, farm condition, tree states, and rehabilitation priorities.
6. **Reports** — export combined results to PDF or DOCX and save forecasts locally.
7. **Database** — reload farms, forecasts, analyses, and reports.
8. **Settings** — control appearance, motion, sound toggles, voice volume, scenario, strategy, simulation size, timeline behavior, and the local Gemini API key.
9. **CoCO-PILOT** — open the floating assistant for concise coconut-farming explanations based on the current analysis or an attached PDF/DOCX report.

## Configuring CoCO-PILOT

1. Create a Gemini API key in Google AI Studio.
2. Open **Settings** in COCO-AID.
3. Paste the key under **CoCO-PILOT / Gemini API** and select **Save key locally**.
4. Open the floating CoCO-PILOT button in the lower-right corner.

The default model is `gemini-flash-latest`. If a saved older model identifier is unavailable, COCO-AID retries with the current stable Flash model. The key is stored only in `data/private_settings.json` on the local computer and that file is excluded from the ZIP and Git. It is not included in reports. Use **Remove saved key** in Settings to delete it.

CoCO-PILOT can use:

- the currently loaded farm and selected forecast date;
- forecast summaries and extreme-weather periods;
- Bayesian and pest-specific risk results;
- land-suitability and farm-condition results;
- the most recently generated saved report;
- an uploaded PDF or DOCX up to 15 MB.

Uploaded document text is stored locally in the cache for the current installation. Do not upload private documents unless you are comfortable sending their extracted content to Gemini when asking a question.

## Official production dataset

Bundled source workbook:

`data/source/COCONUT_PRODUCTION_ALL_PROVINCES_2010_2026_PSA.xlsx`

Processed files:

- `data/official/psa_coconut_production_tidy.csv`
- `data/official/psa_coconut_production_annual.csv`
- `data/official/psa_province_profiles.json`
- `data/official/psa_metadata.json`

Source: Philippine Statistics Authority table `2E4EVCP1`, metric tons, source update 2026-06-04. Completed annual values are used where available. Preliminary and unavailable cells are kept separate from completed official values in the processed provenance.

## Major capabilities

- Liquid-glass agri-tech interface with responsive light/dark themes, controlled translucency, and restrained background animation
- Leaflet farm-polygon drawing and guided first-use coachmarks
- SQLite storage for farms, forecasts, analyses, and reports
- Synchronized Home/popup Weather GIS with radar, satellite reference, rain, temperature, clouds, pressure, wind, point forecasts, and storms
- Cached multi-variable weather cubes and HTTP 429 cooldown handling
- Daily climate-conditioned visual timeline through 2050 with a two-days-per-second playback rate
- Three PSA-calibrated coconut-production series with separate weather-response equations
- Interactive zoomable/pannable production and environmental charts
- Scenario-conditioned drought, extreme rain, heat stress, and typhoon-exposure events
- Date-highlighted hazard timeline with duration, severity, and estimated loss
- Bayesian pest, suitability, and farm-condition donut charts
- Eight pest-specific outbreak assessments with photographs/fallbacks, risk drivers, formulas, and IPM-oriented recommendations
- Seven-state stochastic coconut farm model and expected-utility intervention comparison
- Event-linked rehabilitation heatmaps with selectable hazard dates, inspection schedules, and farm-specific procedures
- Formal PDF and DOCX reports with farm-boundary figure, critical-weather snapshots, pest results, production outlook, provenance, and limitations
- Optional CoCO-PILOT assistant using Gemini, current website context, saved reports, and uploaded PDF/DOCX documents

## Commands

- `setup.bat` — create or repair the path-safe LocalAppData environment, install dependencies, verify data/models/database, and run a smoke check
- `run.bat` — start COCO-AID and open the browser
- `test.bat` — execute the automated tests
- `rebuild_models.bat` — rebuild the development agricultural dataset and model artifacts

Manual start after `setup.bat`:

```powershell
call scripts\activate_environment.bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API documentation: `http://127.0.0.1:8000/docs`

## Data and model boundaries

- The PSA workbook contains provincial aggregates, not individual-farm measurements.
- Farm production, tree health, soil, pest outcomes, and future weather require user observations or model estimates.
- Bundled ML artifacts require validation with real longitudinal coconut-farm records.
- The bundled climate layer is compact development data structured around CMIP6 periods and SSP conventions.
- COCO-AID switches from available short-term numerical forecasts to explicitly labeled stochastic climate-conditioned projections.
- CoCO-PILOT is an explanatory assistant, not a replacement for field inspection, laboratory testing, pesticide labels, or qualified agricultural professionals.
- Generated outputs are decision-support results and are not official prescriptions from PSA, PCA, DA, PAGASA, or another government agency.

## Folder overview

- `app/` — APIs, mathematics, models, climate, weather, simulation, GIS, reports, database, assistant, and frontend
- `data/official/` — processed PSA records and province profiles
- `data/source/` — bundled official source workbook
- `data/climate_demo/` — compact long-term climate development layer
- `data/synthetic/` — reference-based farm-year development dataset
- `artifacts/` — model files and model cards
- `cache/` — provider cache and local assistant document extracts
- `scripts/` — generation, training, and verification tools
- `tests/` — mathematical, unit, API, integration, report, weather, assistant, and data tests
- `docs/` — user, architecture, API, methodology, source, testing, and limitation guides


## Phase 6: Pest-Risk Inference

The PCA-backed `v3.pest_inference` engine is available with five profiles, status-controlled evidence, spatial pressure, conditional/expected loss separation, and migration 6. See `docs/phase_6/`.


## Phase 8 rehabilitation and scenario optimization

The v3 contract API now includes an evidence-linked rehabilitation engine with six mandatory scenario comparisons, transparent costs and labor, budget/labor feasibility, uncertain production outcomes, and safety controls that keep predicted events separate from confirmed damage. See `docs/phase_8/`.

## Phase 8.1 recovery workflow

When manual JSON editing causes a `422 JSON decode error`, keep `run.bat` open and run `resume_phase8_workflow.bat`. Paste the previously returned production forecast ID and pest observation ID when prompted. The helper validates both UUIDs and completes the pest, intercropping, rehabilitation, and retrieval steps using Python-generated JSON.
