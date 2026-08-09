# Phase 2 User Actions

1. Extract the Phase 2 archive into a new folder. Do not overwrite Phase 1.
2. Run `setup.bat`. This installs HTTPX2, applies migrations 1 and 2, verifies source checksums, and seeds PCA reference tables.
3. Run `test.bat`. The expected result is 146 passed with no warning summary.
4. Run `run.bat`.
5. Open `/api/v2/health` and verify contract version `3.0.0-draft.2` and migrations 1 and 2 are applied.
6. Open `/api/v2/data-foundation/summary` and verify the reference counts.
7. Import the restricted farmer registry only when you are ready by running `import_farmer_registry.bat`.

The farmer import is optional for Phase 2 startup. Keep the generated database and backup files private.
