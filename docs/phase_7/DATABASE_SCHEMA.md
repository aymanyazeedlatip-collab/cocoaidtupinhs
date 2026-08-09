# Phase 7 Database Schema

Migration 7, `phase7_intercropping_potential`, adds:

- `intercrop_requirement_profiles`
- `intercrop_assessment_runs`
- `intercrop_cell_assessments`
- `intercrop_component_scores`

Each run preserves the production forecast, optional posterior, optional pest run, weather feature set, weather run, candidate set, cell contexts, parameter versions, summary, warnings, and creation time. Each candidate-by-cell result stores its decomposed components and full provenance.
