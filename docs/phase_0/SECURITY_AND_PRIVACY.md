# Security and Privacy Baseline

## Restricted data

The farmer registry includes direct identifiers. Raw files are not tracked by Git and must not be copied into logs, model prompts, screenshots, public reports, or test fixtures.

## AI boundary

CoCO-PILOT may receive approved analytical summaries and redacted reference excerpts. It must never receive raw farmer names, full registry rows, local API keys, or unrestricted uploaded documents by default.

## Secrets

- `.env` and `data/private_settings.json` remain ignored.
- No API key was found in the supplied source tree during Phase 0 inspection.
- Model and source manifests store hashes, paths, sizes, and scientific metadata, not credentials.

## File safety

Raw inputs are immutable. Derived datasets must be written to staging or processed directories with explicit source hashes so transformations can be reproduced and audited.
