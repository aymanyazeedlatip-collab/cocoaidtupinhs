# Phase 9 Database Schema

Migration 9, `phase9_integrated_decision_support`, creates:

- `decision_support_runs`
- `decision_support_components`
- `decision_support_recommendations`
- `decision_support_trace_edges`

All child records are deleted with their parent decision-support run. Source engine records use restrictive foreign keys and are never cascaded from the integration layer.
