# COCOAID Phase 8.1 JSON Workflow Hotfix

This hotfix improves malformed-JSON diagnostics and removes manual copy/paste risk from the remaining Phase 8 verification workflow.

## Changes

- JSON parse failures now report the exact line, column, character offset, and parser reason.
- Request bodies are not echoed in error responses.
- Added `resume_phase8_workflow.bat` to continue from the pest-assessment step using validated UUID prompts and Python-generated JSON.
- The resume workflow automatically runs pest assessment, intercropping assessment, rehabilitation planning, and saved-plan retrieval.
- Detailed workflow results are written locally under `manual_test_outputs/`, which is excluded from Git.
- Added regression tests for malformed JSON diagnostics and Phase 8 resume payload contracts.

No analytical equations, model artifacts, database migrations, or public API contracts were changed.

## Verification

- 244 automated tests passed across 75 test files.
- The complete resume workflow was executed against a live local FastAPI server from production-forecast verification through saved-plan retrieval.
- Python compilation, JavaScript syntax checks, Phase 0–8.1 verifiers, and archive hygiene checks passed.
