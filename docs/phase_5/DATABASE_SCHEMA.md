# Phase 5 Database Schema

Migration 5 is named `phase5_bayesian_farm_state`.

## Tables

- `bayesian_evidence_observations`: typed observations with evidence status, source, time, value, and unit.
- `bayesian_runs`: execution settings, linkage, dates, seed, particle count, intervention, diagnostics, and warnings.
- `bayesian_posteriors`: state, state intervals, production distribution, probabilities, uncertainty, and provenance.
- `bayesian_parameter_posteriors`: one summarized posterior distribution per uncertain parameter.
- `bayesian_evidence_assimilation`: auditable record of whether and how each observation changed a posterior.

The migration is additive. It does not change the retained production model artifact or delete Phase 1–4 data. Destructive rollback is restricted to disposable test databases.
