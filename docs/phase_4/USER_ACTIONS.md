# Phase 4 User Actions

1. Preserve the Phase 3 folder and ZIP.
2. Extract Phase 4 into a new folder.
3. Do not copy an older `.venv` into the new folder.
4. Run `setup.bat` while connected to the internet.
5. Run `test.bat`; all 185 tests must pass with no warning summary.
6. Run `run.bat`.
7. Confirm `/api/v2/health` reports contract `3.0.0-draft.4` and migration 4 applied.
8. Create a Phase 3 weather assimilation run before requesting a Phase 4 production forecast.
9. Confirm `/api/v2/production/status` reports `v3.production` as available.
10. Keep the raw income workbook, SQLite database, and backups private.

The farmer registry does not need to be imported for Phase 4.
