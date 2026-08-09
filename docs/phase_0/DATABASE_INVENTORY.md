# Legacy Database Inventory

The v2.11 SQLite schema stores the principal farm, analysis, and forecast objects as JSON payloads. This supports rapid prototyping but prevents normalized provenance, relational queries, and independent versioning of observations and model runs.

| Table | Rows in supplied baseline | Columns |
| --- | --- | --- |
| analyses | 0 | id, input_payload, result_payload, metadata_payload, created_at |
| farms | 0 | id, payload, created_at, updated_at |
| reports | 0 | id, analysis_id, report_type, filepath, created_at |
| saved_forecasts | 0 | id, farm_id, name, summary_payload, forecast_payload, created_at, updated_at |

The supplied database contains no saved farm, analysis, report, or forecast records, so the v3 migration can be designed without transforming existing user rows in this specific package. Migration support will still be implemented for compatibility with other installations.
