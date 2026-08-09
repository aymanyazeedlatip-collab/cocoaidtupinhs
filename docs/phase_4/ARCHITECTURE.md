# Phase 4 Architecture: Production Engine Preservation and Upgrade

Phase 4 introduces an executable `v3.production` engine without replacing or retraining the retained `production-synthetic-1.0` artifact.

## Runtime flow

```text
Saved Phase 3 weather feature set
        +
Validated farm and palm inputs
        +
Optional named PCA coconut variety
        ↓
Frozen legacy feature adapter
        ↓
Retained production model
        ↓
Raw annual whole-fruit prediction
        ↓
Bounded named-variety adjustment
        ↓
PCA component conversions
        ↓
Versioned forecast, provenance, shadow comparison, and persistence
```

The engine is intentionally isolated from the future Bayesian engine. Phase 4 stores `posterior_status = not_run` and no posterior interval. Phase 5 will consume the raw and variety-adjusted outputs rather than silently changing the Phase 4 model.

## Module boundaries

- `app/production/feature_adapter.py`: exact 19-feature compatibility boundary.
- `app/production/conversions.py`: named-variety factor and product conversions.
- `app/production/repository.py`: normalized forecast, feature, product, shadow, and actual storage.
- `app/engines/production.py`: orchestration and provenance.
- `app/api/v2/routes.py`: public Phase 4 API.

Scientific calculations remain outside the frontend. The legacy v2.11 API and interface remain available for regression comparison.
