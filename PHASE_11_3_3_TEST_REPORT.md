# COCOAID Phase 11.3.3 Test Report

## Scope

This verification covers the scrollable Home landing page, full-bleed analytical-page backgrounds, guided Farm Profile workflow, farmer helper controls, Leaflet drawing guidance, orange farm-boundary focus state, and preservation of existing frontend/backend contracts.

## Automated tests

- Unit tests: **225 passed**
- Integration tests: **54 passed**
- Mathematical tests: **9 passed**
- Total: **288 passed**

The focused Phase 11.3.3 regression set also verifies that all original Farm Profile analytical field IDs occur exactly once, the Home first section remains one viewport tall while the document scrolls below it, the map focus style is present, section navigation resets scroll position, and the frontend asset version is `11.3.3`.

## Release verification

The following project verification scripts passed in the development tree:

- Phase 1 through Phase 11 verification
- General installation verification
- JavaScript syntax validation for `app/static/app.js` and `app/static/phase11.js`
- Python compilation of the modified interface status module
- Phase 11 static-asset checksum verification

## Layout and interaction validation

A local Chromium layout harness using the actual project HTML and CSS confirmed:

- Desktop Home hero height matches the viewport (1440 × 900 test viewport) while the document continues below it.
- Mobile Home remains scrollable at a 390 × 844 viewport.
- Farm Profile spans the full viewport width.
- Completing the three key Basic Details fields after user interaction advances the guide to Tree Data.
- The large Polygon control dispatches to the underlying Leaflet Draw polygon control selector.
- Completed farm-boundary state applies `grayscale(1) brightness(0.42) contrast(0.92)` to the basemap after transition and displays the orange-boundary success state.

Direct HTTP navigation from the sandboxed Chromium process is blocked by the execution environment's browser policy. Runtime HTTP behavior was therefore validated independently through the actual FastAPI server and route smoke checks rather than represented as a live browser-server session.

## Runtime smoke checks

A fresh Uvicorn startup successfully served the application and health endpoint with HTTP 200 responses. The release route checks cover Home, Phase 11 CSS/JavaScript assets, interface status, and Weather GIS.

## Environment note

The verification environment contains scikit-learn 1.8.0 while archived model metadata expects 1.9.0. The preserved project compatibility path reports this mismatch during model loading. No model artifact or scientific engine was modified by Phase 11.3.3.
