# Privacy and PII Boundary

The farmer workbook and imported names are restricted local data.

- Raw workbook files remain under the ignored `data_sources/raw/` directory.
- Names are stored only in `farmer_identities` and raw quarantine payloads.
- Analytical location, area, tree, parcel, and quality fields are stored separately in `farmer_registry`.
- Identity fingerprints use a local random secret stored in `system_metadata`.
- Public Phase 2 endpoints exclude restricted source records and never return farmer names.
- CoCO-PILOT is not connected to the protected identity table.

Do not commit, publish, email, or upload the raw workbook, a populated SQLite database, or backups to public services.
