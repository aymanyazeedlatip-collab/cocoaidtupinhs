# COCOAID v3 Project Initiation

The COCOAID rehaul is a controlled migration from the frozen v2.11 research prototype.

## Repository state

- `main` preserves the untouched v2.11 source baseline.
- Tag `v2.11-legacy-baseline` identifies the immutable pre-rehaul revision.
- `develop` contains completed Phase 0 and Phase 1 work.
- The legacy UI and `/api/*` routes remain operational.
- The new `/api/v2/*` routes expose v3 contracts and registries.

## Completed phases

1. **Phase 0:** baseline preservation, source/model audit, fixtures, and migration map.
2. **Phase 1:** modular boundaries, strict data contracts, units, provenance, engine/model/parameter registries, structured errors, request tracing, and database migration framework.

## Next phase

**Phase 2: Database Migration and PCA Data Foundation**

Phase 2 will create normalized v3 storage, farmer-registry staging and quality controls, PII separation, and structured PCA variety, pest, fertilization, and intercropping registries.

## Commands

```powershell
# First-time local setup
setup.bat

# Run the preserved application
run.bat

# Run all tests
test.bat

# View or apply database migrations
python scripts\migrations.py status
python scripts\migrations.py upgrade

# Export architecture manifests
python scripts\export_phase1_manifests.py

# Verify the completed Phase 1 package
python scripts\verify_phase1.py
```

## Naming rule

The legacy interface continues to display `COCO-AID` until a compatibility-safe branding migration. New architecture and documentation use `COCOAID` as the product name.
