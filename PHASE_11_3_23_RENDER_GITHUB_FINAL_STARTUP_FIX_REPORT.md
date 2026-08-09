# COCOAID Phase 11.3.23 — Render/GitHub Final Startup Fix

## Root cause

The deployment repository intentionally ignores `data_sources/raw/`, including brochure images, PCA PDFs, income workbooks, and the restricted farmer workbook. Production startup nevertheless called strict source-file verification during reference seeding, so Render failed with `FileNotFoundError` for `csi_brochure_panel_1.jpg`.

## Fix

- Production seeding now uses the committed versioned/checksummed JSON reference catalogs and does not require raw source files at runtime.
- Development/local research seeding remains strict by default and verifies raw source checksums.
- Explicit `verify_files=True` still forces strict verification in any environment.
- The public Git repository can continue excluding `data_sources/raw/`, avoiding accidental publication of restricted farmer data.
- Zero-cost deployment verification now includes a production catalog-seeding regression that fails if startup attempts to hash a raw source file.

## Deployment-reality validation

The release is tested from a Git archive generated after applying `.gitignore`, so the simulated Render checkout contains zero files under `data_sources/raw/`. Production FastAPI startup and `/api/health` must succeed from that checkout.
