# Phase 8 Database Schema

Migration 8, `phase8_rehabilitation_scenario_optimization`, adds:

- `rehabilitation_plan_runs`
- `rehabilitation_actions_v3`
- `rehabilitation_scenario_results`

The plan record links to production, optional Bayesian, optional pest, optional intercropping, and weather runs. Action records preserve trigger and evidence traces. Scenario records preserve all six comparisons, feasibility reasons, utility components, and uncertainty ranges.
