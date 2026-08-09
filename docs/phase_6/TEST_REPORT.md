# Phase 6 Test Report

## Final automated result

```text
210 tests passed across 62 fully isolated test-file processes
```

Each test file runs in a fresh Python process. External pytest plugin autoloading is disabled, the required asyncio plugin is loaded explicitly, numerical-library thread counts are constrained, and emitted diagnostics are configured as errors.

## Phase 6 coverage

- strict pest contracts and validation
- five PCA pest and disease profile loading
- migration 6 fresh upgrade, idempotency, guarded rollback, and re-upgrade
- outbreak-probability bounds
- conditional-loss and expected-loss identity
- predicted and suspected evidence exclusion
- field-confirmed prevalence assimilation
- automatic linkage to Phase 5 Bayesian evidence
- distance-decayed spatial pressure
- Asiatic palm weevil taxonomy separation
- source-linked management actions
- assessment persistence and retrieval
- FastAPI status, observation, assessment, and record endpoints
- legacy endpoint and interface regressions

## Additional verification

- Phase 0 through Phase 6 verification scripts passed
- Python source compilation passed
- main frontend JavaScript syntax passed
- Weather GIS JavaScript syntax passed
- SQLite integrity and foreign-key checks passed
- model artifact checksums remained unchanged
- migration 6 destructive rollback was tested only on disposable databases
- release archive extraction and complete retesting are required before distribution

The development runtime contained scikit-learn 1.8.0 and therefore exercised the preserved model artifacts in disclosed compatibility mode. Normal Windows setup installs the pinned scikit-learn 1.9.0 runtime for exact artifact compatibility.
