# Farmer Registry Import Pipeline

The supplied workbook contains 17,798 rows across 12 worksheets. It is treated as restricted personally identifiable information.

## Commands

Dry run only:

```powershell
python scripts\import_farmer_registry.py --dry-run
```

Back up the current database:

```powershell
python scripts\database_backup.py backup
```

Import after reviewing the dry-run summary:

```powershell
python scripts\import_farmer_registry.py
```

The safer guided Windows workflow is `import_farmer_registry.bat`.

## Validation flags

The importer detects missing location or identity fields, negative values, non-integer counts, coconut area greater than declared area, incompatible zero-area/tree combinations, extreme tree densities, encoding artifacts, and possible duplicate identities.

Records are classified as `accepted`, `flagged`, or `rejected`. Flagged and rejected rows remain available for audit; they are never silently corrected or deleted.
