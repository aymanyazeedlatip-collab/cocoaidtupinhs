# Phase 6 Database Schema

Migration 6: `phase6_pest_risk_inference`.

New tables:

- `pest_observations_v3`
- `pest_assessment_runs`
- `pest_assessments_v3`
- `pest_assessment_contributions`
- `pest_assessment_actions`

The schema stores complete request context, linked production/weather/posterior IDs, every evidence contribution, source-backed management actions, and immutable provenance. A pest prevalence observation can also reference the corresponding Phase 5 Bayesian evidence record.
