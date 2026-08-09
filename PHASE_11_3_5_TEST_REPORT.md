# COCOAID Phase 11.3.5 Test Report

## Release under test

- Interface version: `phase11-agritech-interface-1.3.5`
- Design system: `cocoaid-official-agritech-1.3.5`
- Scope: Home enrichment, progressive Farm Profile, explicit edit-save workflow, loading hologram, and Long-Term Model Forecast UX/integration changes.

## Automated regression inventory

All automated test groups passed in the working release tree:

- Unit: **244 passed**
- Integration: **54 passed**
- Mathematical: **9 passed**
- Total: **307 passed**

Dedicated Phase 11.3.5 tests cover the map-first Farm Profile workflow, forecast-button completion gate, grouped input stages, dedicated boundary-edit save control, orange loading treatment, provider/model timeline labels, automatic forecast controls, adaptive farm framing, compact Weather GIS map controls, removal of farmer-facing scenario/strategy/run controls, and preservation of legacy DOM/API contracts.

## Release verifiers

Passed:

- Phase 1 through Phase 11 release verifiers
- General installation verifier
- Phase 11 asset checksum/integrity verification

Phase 0 is not asserted from the distributable ZIP because its baseline-preservation verifier requires original Git tag/repository metadata, which is not carried in the release archive.

## Frontend and syntax verification

Passed:

- `node --check app/static/app.js`
- `node --check app/static/phase11.js`
- Python compilation of the application
- Static DOM checks for unique IDs and required workflow/control elements
- Focused Phase 11.3.5 frontend/API regression tests

The execution environment blocks direct automated browser navigation to localhost/file URLs, so this report does **not** claim end-to-end browser automation. Runtime HTTP routes are verified separately through a live Uvicorn process.

## Runtime and route verification

Fresh Uvicorn startup is checked against the packaged release. Verified routes include:

- `/`
- `/api/health`
- `/api/v2/interface/status`
- `/static/phase11.css?v=11.3.5`
- `/static/phase11.js?v=11.3.5`
- `/weather-viewer`

## Model-runtime environment note

`requirements.txt` pins `scikit-learn==1.9.0`, matching the archived model artifacts. This sandbox currently provides scikit-learn 1.8.0, so local verification logs may show compatibility-mode warnings. That warning is caused by the sandbox environment rather than the packaged project requirements.

## Scientific-source boundary retained

The first available 16-day window is identified as the genuine Open-Meteo numerical forecast window. Dates beyond the provider horizon are explicitly identified as climate-conditioned modeled weather through 2050. The existing production ML model consumes this weather path, but COCOAID does not misrepresent post-provider weather as observed or provider-issued forecast data. Development-set performance metrics shown on Home remain labeled as synthetic/reference-based research benchmarks rather than field-validated accuracy claims.
