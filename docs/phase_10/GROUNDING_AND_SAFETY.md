# Grounding and Safety

CoCO-PILOT is grounded in the saved Phase 9 record and public PCA reference metadata. It excludes restricted farmer records and recursively removes name, email, phone, identity, and raw-payload fields.

The deterministic provider is always available. The optional Google AI provider receives only the redacted package and deterministic draft. Its output is accepted only when it does not introduce new numeric values or dosage-like instructions. Any provider or validation failure falls back to the deterministic explanation.

The report layer generates numeric tables directly from stored structured values.

Scenario-comparison mode uses all six saved Phase 8 scenarios. Work-plan mode uses only action IDs attached to the selected feasible scenario.
