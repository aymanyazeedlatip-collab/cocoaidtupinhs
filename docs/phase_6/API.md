# Phase 6 API

```text
GET  /api/v2/pests/status
GET  /api/v2/pests/profiles
POST /api/v2/pests/observations
GET  /api/v2/pests/observations
POST /api/v2/pests/assess
GET  /api/v2/pests/assessments
GET  /api/v2/pests/assessments/{assessment_id}
```

A pest assessment requires an existing Phase 4 production forecast. A Phase 5 posterior is optional and, when supplied, its production median becomes the loss baseline.

Supplying `prevalence_fraction` to the observation endpoint creates a linked Phase 5 `pest_prevalence` observation. Symptom-only observations do not invent a prevalence value and therefore do not create the Bayesian link.
