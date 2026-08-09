# Production Output Layers

Phase 4 exposes three distinct layers and does not merge them:

1. **Raw ML prediction**: direct retained-model output, interpreted as annualized whole-fruit mass with husk in tonnes.
2. **Variety-adjusted prediction**: raw output multiplied by a bounded within-class PCA reference factor.
3. **Bayesian posterior prediction**: explicitly absent in Phase 4 and marked `not_run`.

This separation prevents a deterministic reference adjustment from being presented as Bayesian inference.

## Shadow comparison

When the caller provides `baseline_annual_production_tons`, COCOAID reproduces the bounded v2.11 correction for comparison only:

```text
legacy = baseline × (0.90 + 0.10 × clip(raw_model / baseline, 0.65, 1.35))
```

The legacy comparison is not used to overwrite the v3 output.
