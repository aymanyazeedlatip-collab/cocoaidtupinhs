# Phase 7 Data Contracts

Contract API version: `3.0.0-draft.7`.

Primary contracts:

- `IntercropCellContext`: cell area, palm age, spacing, design, canopy density, slope, drainage, soil pH, soil moisture, nitrogen, available space, management feasibility, and market access.
- `IntercropAssessmentRequest`: production linkage, optional Bayesian and pest linkage, candidate set, cells, assessment time, and farm-data version.
- `CanopyLightEstimate`: transmitted light, source PCA rows, interpolation method, bounded density/orientation adjustments, and understory radiation.
- `SuitabilityComponent`: score, weight, hard-constraint status, and explanation.
- `IntercropCandidateAssessment`: candidate-by-cell score, class, limiting factors, competition, pest conflict, planting window, layout, economics, confidence, and provenance.
- `IntercropEngineOutput`: complete run, summary, versions, weather lineage, warnings, and data notice.

Unknown fields are rejected. Cell IDs must be unique within one request. Any hard-constraint failure caps suitability at 40.
