# Phase 9 Architecture: Integrated Decision-Support Network

Phase 9 adds a deterministic integration layer above the versioned production, Bayesian, pest, intercropping, and rehabilitation records. It does not replace, recompute, or mutate the source engines.

## Processing boundary

```text
Production forecast (required)
   ├── Bayesian posterior (optional)
   ├── Pest assessment run (optional)
   ├── Intercropping run (optional)
   └── Rehabilitation plan (optional)
                ↓
        Dependency validation
                ↓
     Component status resolution
                ↓
    Evidence-linked recommendations
                ↓
 Consolidated decision-support record
```

The production forecast is mandatory because every downstream assessment is linked to it. Optional components may be skipped or fail without destroying valid results when `failure_policy=continue_optional`. The `strict` policy aborts the run when a requested optional record is invalid or missing.
