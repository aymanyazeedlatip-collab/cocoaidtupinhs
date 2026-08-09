# Phase 6.2: Windows Setup Path Hotfix

- Moved the Windows virtual environment to a short LocalAppData path to prevent legacy `MAX_PATH` failures in deep packages such as `lxml`.
- Added a shared environment resolver used by setup, run, tests, weather diagnostics, farmer import, and model rebuild scripts.
- Added repair behavior for incomplete environments.
- Installed a binary `lxml` wheel before the remaining requirements and verified the runtime import.
- Disabled the pip download cache during setup to avoid retaining partial package extractions.
- Added a flat release ZIP layout so extraction does not create a duplicate nested release directory.
- Added setup-path regression tests and updated troubleshooting instructions.

## Verification

- 219 automated tests pass across 64 test files.
- Python compilation and frontend JavaScript syntax checks pass.
- The exact deep `lxml` Schematron resource that failed in Phase 6.1 is verified after installation.
