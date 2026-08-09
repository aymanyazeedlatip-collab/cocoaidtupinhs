# Phase 2 Architecture: Database Migration and PCA Data Foundation

Phase 2 adds a normalized, provenance-linked data foundation beside the preserved v2.11 JSON tables. It does not replace the legacy analytical engines.

## Data layers

1. **Immutable raw sources** under `data_sources/raw/`.
2. **Versioned reference catalogs** under `data/reference/`.
3. **Normalized SQLite tables** created by migration 2.
4. **Privacy-safe read APIs** under `/api/v2/data-foundation`.

## Reference flow

```text
PCA PDFs, brochure images, and workbook
        -> checksum-verified source registry
        -> transcribed/versioned JSON catalogs
        -> idempotent database seeding
        -> read-only v2 API endpoints
```

## Farmer registry flow

```text
Restricted XLSX
  -> streaming XML reader
  -> normalization and validation
  -> quarantined raw/normalized staging records
  -> protected identity table
  -> pseudonymous analytical registry
  -> privacy-safe aggregate API
```

The farmer workbook is not imported automatically. The explicit import utility performs a dry run and backup before storage.
