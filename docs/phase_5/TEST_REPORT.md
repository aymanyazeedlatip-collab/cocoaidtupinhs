# Phase 5 Test Report

Warnings are treated as errors through `pytest.ini`.

Final release target:

```text
197 tests passed across 2 isolated batches
```

The isolated-batch runner executes every discovered `test_*.py` file exactly once while avoiding cumulative process-state interference from the large preserved v2.11 regression suite.

Coverage includes:

- all Phase 0–4 regression tests;
- migration 5 fresh install, idempotency, populated rollback, and re-upgrade;
- strict evidence-type/unit validation;
- exact initial-state versus prior-posterior exclusivity;
- deterministic seeded simulation;
- palm-position conservation;
- posterior state and parameter intervals;
- predicted/suspected evidence exclusion;
- confirmed-evidence updating and resampling diagnostics;
- sequential posterior updating;
- production-posterior linkage without ML retraining;
- API and OpenAPI contracts;
- database integrity and foreign-key checks;
- Python and JavaScript syntax verification;
- archive extraction and complete retesting.
