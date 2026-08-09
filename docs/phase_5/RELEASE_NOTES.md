# COCOAID v3 Phase 5 Release Notes

- Added migration 5 and normalized Bayesian observation/run/posterior storage.
- Added executable `v3.bayesian` engine version `1.0.0`.
- Added seven-state palm dynamics plus soil-fertility and soil-water propagation.
- Added 100–5,000-particle sequential importance/resampling simulation.
- Added deterministic seeds and posterior parameter carry-forward.
- Added reliability-gated evidence: predicted and suspected values never update posterior weights.
- Added 5th–95th percentile state and production outputs.
- Added decline, recovery, mortality, and pest-outbreak probabilities.
- Added linkage that fills the Phase 4 posterior layer without changing ML weights.
- Added a complete two-batch test runner for the preserved legacy and v3 suites.
