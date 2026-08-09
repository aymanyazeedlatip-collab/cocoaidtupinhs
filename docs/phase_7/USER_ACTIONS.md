# Phase 7 User Actions

This checklist is self-contained. The release response also provides the exact JSON bodies needed for weather assimilation, production forecasting, optional pest assessment, and intercropping assessment.

1. Extract Phase 7 into a new short folder such as `C:\COCOAID\P7`.
2. Run `setup.bat` and confirm Phase 7 verification passes.
3. Run `test.bat` and confirm the reported final test total has no warning or failure summary.
4. Run `check_weather_provider.bat`.
5. Run `run.bat` and verify `/api/v2/health`, `/api/v2/intercropping/status`, and `/api/v2/intercropping/candidates`.
6. Create a weather feature set and production forecast.
7. Optionally create a Phase 6 pest assessment and copy its `output.run_id`.
8. Run `POST /api/v2/intercropping/assess` with one or more cells and candidates.
9. Confirm every result exposes component scores, limiting factors, canopy-light trace, competition risk, pest-conflict risk, confidence, and provenance.
