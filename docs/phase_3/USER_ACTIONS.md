# Phase 3 User Actions

1. Keep the Phase 2 archive as an untouched backup.
2. Extract the Phase 3 archive into a new folder.
3. Do not copy the previous `.venv`, database, or cache into the new folder for the first clean test.
4. Run `setup.bat` while connected to the internet.
5. Run `test.bat` and confirm the exact passing-test count shown in the Phase 3 release notes with no warning section.
6. Run `run.bat`.
7. Open `/api/v2/health` and confirm contract version `3.0.0-draft.3` and migration 3 is applied.
8. Open `/api/v2/weather/status` and confirm `live_forecast_limit_days` is 16.
9. Use `/docs` to run `POST /api/v2/weather/assimilate` for a test location.

No manual database migration is required. Setup applies migration 3 automatically and preserves existing legacy and Phase 2 tables.

A first successful online weather request is required before offline cached weather can be available. Do not repeatedly force-refresh during a provider cooldown.
