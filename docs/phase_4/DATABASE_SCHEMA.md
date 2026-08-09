# Phase 4 Database Schema

Migration 4 is named `phase4_production_engine`.

## Production tables

- `production_feature_snapshots`: exact ordered model payload, SHA-256, sources, flags, and warnings.
- `production_forecasts_v3`: raw, variety-adjusted, and future posterior fields with model and adapter versions.
- `production_product_estimates`: traceable product conversions.
- `production_shadow_comparisons`: legacy-vs-v3 comparison without changing the v3 result.
- `production_actuals`: measured, farmer-reported, or government production outcomes.

## Intercropping economics

- `intercrop_economic_profiles`: sanitized aggregate cacao and coffee profiles. It contains no names or row-level records.

Migration 4 is additive, checksummed, idempotent, and guarded against accidental destructive rollback. It preserves all Phase 1–3 tables.
