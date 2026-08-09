# COCOAID Phase 11.3.9 Release Notes

Phase 11.3.9 refines Satellite imagery, Extreme Weather Detection, and Farm Health Monitoring without changing the preserved analytical contracts.

## Productivity Satellite
- Replaced the forecast Satellite implementation with a dedicated NASA GIBS WMTS tile pane above the normal map base.
- The OpenStreetMap base is dimmed while Satellite is active and restored when Satellite is disabled.
- Uses MODIS Terra corrected-reflectance true-color imagery with native tile upscaling for higher Leaflet zoom levels.

## Extreme Weather Detection
- Filled the Selected Threat card with a weather-event icon and interactive farm-scale Leaflet event map.
- Added a news-style event-intensity visualization derived from the selected farm event severity. It is a visualization, not radar imagery.
- Added nearest-frame rain, temperature, wind, and humidity details.
- Increased calendar date/ping separation to prevent event markers from covering date numbers.
- Changed Technical Comparison to an orange/red severity/loss palette.

## Farm Health Monitoring
- Increased text sizes, line heights, card spacing, and chart-panel spacing.
- Rehabilitation map now recalculates the exact farm-bound center and adaptive zoom after invalidating Leaflet size.
- Selecting a different rehabilitation event refreshes Bayesian pest pressure and suitability using the nearest weather frame and selected event severity; Farm Condition uses the corresponding forecast state.
- Replaced the static inspection/rehabilitation/follow-up cards with an interactive month calendar containing event, inspection, rehabilitation, 30-day follow-up, and 90-day review phases.

## Verification
- 339 tests collected and passed across unit, integration, and mathematical suites.
- Phase 11 verification and installation verification passed.
- JavaScript syntax, Python compilation, CSS parsing, and duplicate-DOM-ID checks passed.
- Fresh runtime HTTP checks returned 200 for Home, health, interface status, Phase 11 CSS/JS, and Weather GIS.

Interface version: `phase11-agritech-interface-1.3.9`
Design system version: `cocoaid-official-agritech-1.3.9`
