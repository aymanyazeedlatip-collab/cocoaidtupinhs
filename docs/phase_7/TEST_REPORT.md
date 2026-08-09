# Phase 7 Test Report

## Result

The complete COCOAID regression and Phase 7 test suite passed:

- **231 tests passed**
- **69 fully isolated test-file processes**
- No failed tests
- No skipped tests
- Pytest warnings remain configured as errors

## Phase 7-specific coverage

The suite verifies:

- strict Phase 7 request and response contracts;
- 35 versioned intercrop requirement profiles;
- PCA canopy-light row selection and age interpolation;
- bounded canopy-density and row-orientation adjustments;
- nine decomposable suitability components;
- weighted geometric aggregation;
- hard light and slope constraint enforcement;
- coconut competition penalties;
- pest-conflict and ecological-benefit adjustments;
- cacao and coffee gross-revenue potential using sanitized aggregate profiles;
- explicit `not_available` economics for crops without supported economic data;
- persistence and retrieval of runs, cell assessments, component scores, and provenance;
- Phase 6 pest-assessment linkage;
- migrations 1 through 7, idempotency, destructive rollback, and re-upgrade;
- SQLite integrity and foreign-key checks;
- legacy endpoint and frontend regression behavior.

## Independent release checks

The release verification also checks:

- Python compilation;
- JavaScript syntax for the main application and Weather GIS;
- model artifact checksums;
- contract, engine, parameter, endpoint, migration, and requirement manifests;
- absence of generated databases, virtual environments, caches, and secrets from the release archive;
- clean ZIP extraction and repeatable execution.

## Known testing boundary

The intercropping engine is an evidence-based scoring engine, not a field-validated supervised machine-learning model. Non-light agronomic thresholds are versioned development assumptions and remain explicitly labeled for expert review and later calibration.
