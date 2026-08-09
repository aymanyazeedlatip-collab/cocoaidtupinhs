# COCOAID v3 Phase 5: Bayesian Farm-State Simulator

- Contract API: `3.0.0-draft.5`
- Migration: `phase5_bayesian_farm_state`
- Bayesian engine: `v3.bayesian` version `1.0.0`
- Parameter version: `bayesian-farm-state-parameters-1.0.0`
- Method: seeded sequential importance/resampling particle filter

The release connects the preserved Phase 4 production baseline to a dynamic probabilistic farm-state model. It stores evidence, posteriors, parameter summaries, uncertainty, diagnostics, and complete provenance. Predicted and suspected records are never treated as confirmed evidence.

See `docs/phase_5/` for architecture, contracts, method, limitations, tests, API examples, and user actions.
