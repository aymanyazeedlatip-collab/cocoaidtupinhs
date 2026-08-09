# Phase 6.2 Setup Path Hotfix: User Actions

This release fixes Windows package installation failures caused by deeply nested project and `lxml` paths.

1. Create a short folder, preferably `C:\COCOAID\P6_2`.
2. Extract the ZIP contents directly into that folder. The ZIP is intentionally flat, so it does not add a second duplicate release folder.
3. Do not copy the failed `.venv` from Phase 6.1.
4. Run `setup.bat` while connected to the internet.
5. Confirm that setup prints a path similar to `%LOCALAPPDATA%\COCOAID\venvs\phase6_2_py311` and finishes with `SETUP COMPLETE`.
6. Run `test.bat` and confirm the full suite passes.
7. Run `check_weather_provider.bat`, then continue the Phase 6 API verification from `POST /api/v2/weather/assimilate`.

The virtual environment is intentionally stored outside the extracted project. Runtime launchers read its location from `.cocoaid_venv_path` automatically.
