# Phase 1 Test Report

## Test sequence

1. Baseline suite before Phase 1 changes: **111 passed**.
2. Python source compilation after implementation: passed.
3. Complete automated suite after Phase 1 implementation: **135 passed**.
4. Installation and analytical smoke verification: passed.
5. Migration upgrade, idempotency, legacy-schema adoption, guarded rollback, and re-upgrade: passed.
6. Legacy and `/api/v2` coexistence smoke tests: passed.
7. Contract JSON Schema generation and validation: passed.
8. Model checksum, feature schema, and runtime-status checks: passed.

## New coverage

- Strict contract rejection of unknown fields
- Farm and coconut-area consistency
- Timezone-aware observations
- Production period and unit validation
- 16-day numerical forecast limit
- Required weather units
- Predictive interval ordering
- Palm-state validity
- Conditional versus expected pest loss
- Intercrop hard constraints
- Rehabilitation cost and budget invariants
- Explicit unit conversions
- Stable schema hashes
- Engine validation and exception wrapping
- Descriptor-only planned engines
- Checksummed migration lifecycle
- v2 API registry endpoints
- Structured errors and request IDs
- Legacy API preservation

## Known test-environment condition

The build container provided scikit-learn 1.8.0, while the preserved artifacts require 1.9.0 for exact serialization compatibility. The registry detected and reported this mismatch. The suite passed with all three artifacts available in compatibility mode. `requirements.txt` now pins 1.9.0 for fresh local setup.
