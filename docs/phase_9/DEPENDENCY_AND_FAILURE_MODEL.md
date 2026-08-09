# Dependency and Failure Model

The versioned dependency graph is `decision-support-dependency-graph-1.0.0`.

- Production has no upstream analytical dependency inside Phase 9.
- Bayesian, pest, intercropping, and rehabilitation records must belong to the same farm and production forecast.
- Missing optional records are disclosed as `skipped`.
- Invalid or mismatched records are disclosed as `failed` under `continue_optional`.
- Under `strict`, a requested invalid record terminates the run with an explicit engine error.
- A partial run is stored only when its production baseline is valid.

The integration layer preserves successful source outputs and does not invent fallback analytical values.
