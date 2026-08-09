# Regression-Test Baseline

The preserved v2.11 application was tested before architectural refactoring.

- Test command: `pytest -q`
- Audit runtime: Python 3.13.5
- Result: **111 passed**
- Warnings: **11 scikit-learn artifact compatibility warnings**
- Runtime: approximately 15 seconds in the audit environment

The warnings state that estimators serialized with scikit-learn 1.9.0 were loaded under scikit-learn 1.8.0. They do not cause current test failures, but they are recorded as a Phase 1 reproducibility risk.

Tests were executed with a temporary SQLite database, report directory, and cache directory so the preserved project state was not contaminated by test-generated records or reports.

Full console output is stored in `baseline_snapshots/test_results.txt`.
