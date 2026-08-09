# Phase 2 Database Schema

Migration 2, `phase2_normalized_data_foundation`, adds the following table groups.

## Provenance and metadata

- `system_metadata`
- `source_documents`

## PCA reference knowledge

- `coconut_varieties`
- `variety_parameters`
- `pest_profiles`
- `pest_evidence_rules`
- `pest_management_actions`
- `intercrop_candidates`
- `canopy_light_parameters`
- `fertilization_scenarios`

## Restricted farmer registry

- `farmer_import_runs`
- `farmer_registry_staging`
- `farmer_identities`
- `farmer_registry`
- `farmer_quality_flags`

Foreign keys are enabled on every application connection. Migration checksums prevent changed migration code from being silently accepted. Migration 2 rollback is destructive and requires the explicit `--allow-destructive` flag; it must only be used against disposable test databases.
