# Phase 8 Test Report

## Release gate

Phase 8 passed the complete COCOAID regression and analytical test inventory before packaging.

```text
239 tests passed
73 fully isolated test-file processes
0 failures
```

Warnings remain configured as errors through `pytest.ini`. A warning would therefore fail its test process rather than be omitted from the result.

## Phase 8 coverage

The Phase 8 tests verify:

- rehabilitation request and response contracts;
- exact palm-state conservation in every planning cell;
- separation of predicted, suspected, and confirmed damage evidence;
- generation of all six required scenarios;
- permanent inclusion of the no-action comparator;
- budget and labor feasibility checks;
- expected-utility ranking under risk aversion;
- pest-treatment gating behind confirmed evidence;
- pre-event preparation versus post-event rehabilitation;
- action cost, labor, recovery, confidence, and follow-up fields;
- linked Phase 4 production, Phase 5 posterior, Phase 6 pest, and Phase 7 intercropping records;
- database persistence and retrieval;
- API execution and structured error behavior;
- migration 8 installation, idempotency, rollback, re-upgrade, SQLite integrity, and foreign-key integrity.

## Full-project regression coverage

The release gate also includes all existing Phase 0 through Phase 7 tests, legacy v2.11 endpoint and UI regressions, model checksum checks, contract validation, weather/production/Bayesian/pest/intercropping integrations, Windows external-environment path checks, and setup verification.

## Manual external dependency

Automated tests use deterministic stored or mocked inputs. After extraction on Windows, the user must run `check_weather_provider.bat` once to verify the current machine can reach Open-Meteo through its local DNS, TLS, and proxy configuration. This external network check is not claimed as completed inside the packaging environment.
