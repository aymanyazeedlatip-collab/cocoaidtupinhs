# Database Migration Framework

Phase 1 introduces ordered and checksummed SQLite migrations without normalizing the data model yet. Normalized v3 tables belong to Phase 2.

## Current migration

| Version | Name | Purpose |
| --- | --- | --- |
| 1 | `legacy_v211_schema_baseline` | Reproduce and adopt the four v2.11 tables and indexes |

The migration safely upgrades older `reports` tables by adding `report_type` while retaining existing records.

## Commands

```powershell
python scripts\migrations.py status
python scripts\migrations.py upgrade
```

A rollback of migration 1 would delete the legacy tables, so it is blocked unless explicitly invoked in a disposable database:

```powershell
python scripts\migrations.py downgrade-one --allow-destructive
```

Do not use the destructive command on a real installation. Create a database backup first. Phase 2 migrations must provide non-destructive upgrade paths and tested rollback or restoration procedures.

## Integrity controls

- Migration versions are unique and ordered.
- Applied names and SHA-256 checksums are stored in `schema_migrations`.
- A changed migration checksum stops startup rather than silently applying altered history.
- Re-running `upgrade` is idempotent.
- Failed migrations are rolled back and converted to a structured migration error.
