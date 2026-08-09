# COCO-AID API v2.4

Interactive OpenAPI documentation is available at `/docs` while the server is running.

## Core

- `GET /api/health`
- `GET /api/config`
- `GET /api/sources`
- `GET /api/models`
- `GET /api/models/{model_name}`

## Official PSA production

- `GET /api/official-data/summary`
- `GET /api/official-data/provinces`
- `GET /api/official-data/profile?province=South%20Cotabato&region=...`

Profiles include three product histories, 2025 official values, 2026 estimates, quarter shares, reference level, and source metadata.

## Farm storage

- `POST /api/farms`
- `GET /api/farms`
- `GET /api/farms/{farm_id}`
- `PUT /api/farms/{farm_id}`
- `DELETE /api/farms/{farm_id}`

## Weather

- `POST /api/weather/point`
- `GET /api/weather/point`
- `POST /api/weather/grid`
- `POST /api/weather/frame`
- `POST /api/weather/cube`
- `GET /api/weather/radar/frames`
- `GET /api/weather/storms`
- `GET /api/weather/warnings`
- `GET /api/weather/geocode`

Compatibility aliases support the embedded Weather GIS.

## Climate and farm analytics

- `POST /api/climate/projection`
- `POST /api/climate/generate-trajectory`
- `POST /api/farm-assessment`
- `POST /api/pest-risk/evaluate`
- `POST /api/suitability/evaluate`
- `POST /api/simulation/run`
- `POST /api/farm-site/forecast`
- `POST /api/scenarios/compare`
- `POST /api/rehabilitation-map` - legacy current-condition rehabilitation grid
- `POST /api/rehabilitation-plan` - separate event-conditioned green/yellow/red heatmaps and schedules
- `POST /api/analysis/full`
- `GET /api/analysis/{analysis_id}`

`/api/farm-site/forecast` returns weekly agricultural control points plus daily visual frames through the chosen end year, annual three-product values, posterior intervals, extreme events, provider-merge metadata, and PSA calibration provenance. The extreme events can be passed to `/api/rehabilitation-plan`.

## Reports and database

- `POST /api/reports/generate` — `report_format` is `pdf` or `docx`
- `GET /api/reports/{report_id}`
- `GET /api/database/summary`
- `GET /api/database/analyses`
- `DELETE /api/database/analyses/{analysis_id}`
- `GET /api/database/reports`
- `POST /api/database/forecasts`
- `GET /api/database/forecasts`
- `GET /api/database/forecasts/{forecast_id}`
- `DELETE /api/database/forecasts/{forecast_id}`

A report request may provide both `analysis_id` and supplemental `analysis.farm_site_forecast` and `analysis.rehabilitation_event_plans`; the stored analysis remains authoritative and only known supplemental report sections are merged.


## Pest-specific risk

`POST /api/pest-risk/specific` returns eight condition-sensitive coconut-pest outbreak-priority scores, local illustration URLs, risk drivers, calculation terms, and inspection-oriented recommendations. Scores are 0-100 decision-support priorities, not laboratory identifications.

## CoCO-PILOT assistant endpoints

- `GET /api/assistant/status` - configuration status, preferred the current compatible Flash model model, and resolved fallback model
- `POST /api/assistant/configure` — save a Gemini API key locally
- `DELETE /api/assistant/configure` — remove the locally saved key
- `POST /api/assistant/upload-document` — extract a PDF or DOCX into a temporary local assistant document
- `POST /api/assistant/attach-report/{report_id}` — attach an existing saved report
- `POST /api/assistant/chat` — request a compact Gemini response using optional farm/forecast context and up to three documents

Uploads are limited to 15 MB. Extracted document context is length-limited. Gemini failures and free-tier limits are returned as clear service-unavailable errors. The backend prefers `gemini-flash-latest` and retries with `gemini-flash-latest` when a configured legacy model has been retired or is unavailable.

## COCOAID v3 weather assimilation

Phase 3 adds versioned endpoints under `/api/v2/weather`:

- `GET /api/v2/weather/status`
- `POST /api/v2/weather/assimilate`
- `GET /api/v2/weather/runs`
- `GET /api/v2/weather/runs/{run_id}`
- `GET /api/v2/weather/runs/{run_id}/features`
- `GET /api/v2/weather/compare`

The live payload contains current conditions and no more than 16 forecast days. Historical provider values may be stored for lagged feature engineering but are not displayed as future weather.


## COCOAID v3 Phase 4 production engine

- `GET /api/v2/production/status`
- `POST /api/v2/production/forecast`
- `GET /api/v2/production/forecasts`
- `GET /api/v2/production/forecasts/{forecast_id}`
- `POST /api/v2/production/actuals`
- `GET /api/v2/production/forecasts/{forecast_id}/performance`

## COCOAID v3 Phase 5 Bayesian simulator

- `GET /api/v2/bayesian/status`
- `POST /api/v2/bayesian/observations`
- `GET /api/v2/bayesian/observations`
- `POST /api/v2/bayesian/simulate`
- `GET /api/v2/bayesian/posteriors`
- `GET /api/v2/bayesian/posteriors/{posterior_id}`

The first simulation supplies an initial state; a sequential simulation supplies a prior posterior instead. Predicted and suspected observations are retained but not assimilated. See `docs/phase_5/API.md`.
