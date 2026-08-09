# External data-source handling

`data_sources/raw/` contains the user-supplied PCA references, brochure photographs, and farmer registry workbook used to initialize the COCOAID v3 rehaul. This directory is intentionally ignored by Git because it includes large source documents and personally identifiable farmer data.

Rules:

- Treat the farmer workbook as restricted raw input.
- Never send farmer names to external AI services.
- Do not use PCA reference sheets as farm-level supervised training records.
- Digitized parameters must retain document, page/section, encoder, verifier, unit, and confidence fields.
- Raw files are immutable. Derived or cleaned records belong in a separate staging or processed layer.
