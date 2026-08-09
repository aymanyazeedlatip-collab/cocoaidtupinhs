# Phase 8 Data Contracts

Contract API version: `3.0.0-draft.8`.

Primary contracts:

- `RehabilitationCellContext`: exact palm-state inventory plus soil, drainage, production, damage, and operational context.
- `RehabilitationPlanRequest`: linked analytical IDs, cells, budget, labor, horizon, discounting, risk aversion, and farm-data version.
- `RehabilitationTrigger`: source, severity, evidence status, confirmation state, and evidence identifiers.
- `RehabilitationAction`: problem, cause, trigger trace, timing, instructions, materials, costs, labor, recovery range, confidence, and confirmation requirement.
- `RehabilitationScenarioResult`: feasibility, action IDs, coconut interval, gross intercrop revenue interval, severe-loss probability, cost, labor, and comparative utility.
- `RehabilitationPlan`: all candidate actions, six scenarios, selected feasible scenario, no-action reference, budget remainder, provenance, warnings, and limitations.
