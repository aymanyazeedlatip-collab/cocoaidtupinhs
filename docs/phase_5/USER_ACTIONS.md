# Phase 5 User Actions

1. Preserve the Phase 4 folder and ZIP.
2. Extract Phase 5 into a new folder; do not copy the old `.venv`.
3. Run `setup.bat` while connected to the internet.
4. Run `test.bat`; both isolated batches must complete and the final line must report 197 tests passed.
5. Run `run.bat`.
6. Confirm `/api/v2/health` reports contract `3.0.0-draft.5` and migrations 1–5 applied.
7. Confirm `/api/v2/bayesian/status` reports `v3.bayesian` version `1.0.0` as available.
8. Create a Phase 3 weather run and Phase 4 production forecast before a Bayesian simulation.
9. For the first simulation, provide `initial_state`. For later updates, provide `prior_posterior_id` instead.
10. Do not label a model prediction as field evidence. `predicted` and `suspected` observations are intentionally not assimilated.
11. Preserve the random seed when you need an exactly reproducible result.
12. Keep the local database and any farmer-identifiable source files private.
