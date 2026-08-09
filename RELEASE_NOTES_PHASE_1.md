# COCOAID v3 Phase 1 Release Notes

Phase 1 establishes the architecture required for the full COCOAID rehaul without replacing the working v2.11 prototype.

## Added

- Strict versioned data contracts for farms, cells, cohorts, observations, production, weather runs, weather features, forecasts, Bayesian posteriors, pest assessments, intercrop assessments, rehabilitation plans, and complete analysis runs
- Canonical unit registry and explicit conversions
- Data-source and run-provenance contracts
- Analytical engine abstraction and dependency catalog
- Parameter registry and expanded model registry
- `/api/v2` contract and architecture endpoints
- Structured error responses, request IDs, and request timing
- Checksummed SQLite migration framework
- Phase 1 manifests, verification script, and user instructions

## Preserved

- Existing v2.11 frontend and route contracts
- Existing model artifacts and their checksums
- Existing SQLite tables and records
- Existing analytical and reporting behavior

## Validation

- 111 tests passed before implementation
- 135 tests passed after implementation
- Installation and analytical smoke verification passed
- Migration upgrade, idempotency, guarded rollback, and legacy-schema adoption passed

## Required local verification

Run `setup.bat`, then `test.bat`, then inspect `/api/v2/health`. Exact model reproducibility requires `model_runtime.compatible: true` under scikit-learn 1.9.0.
