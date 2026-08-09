# COCOAID Phase 11.3.6 Release Notes

## Scope
Phase 11.3.6 refines the Productivity and Hazard Intelligence user interfaces while preserving the existing analytical contracts and backend engines.

## Productivity / Long-Term Model Forecast
- Removed the duplicated embedded Weather GIS iframe from the Productivity page.
- Moved the dedicated Weather GIS navigation item to the final position in the primary navigation list.
- Rebuilt Long-Term Model Forecast as a full-viewport Leaflet map workspace.
- Moved forecast summary, map layers, analytical graphs, and timeline into independent floating controls.
- Side drawers are mutually exclusive so graph/layer/summary panels do not stack over one another.
- The timeline can be collapsed independently.
- Added a Satellite map filter using NASA EOSDIS GIBS MODIS Terra true-color imagery.
- Replaced the former single wind marker with Weather GIS-style animated wind particles/arrows.
- Wind rendering uses the provider weather grid and provider elevation grid for visualization-scale terrain deflection during the live provider window.
- Preserved farm auto-framing and adaptive zoom.

## Forecast temporal resolution
- The first 16 days now use the same quarter-hour visualization method as the dedicated Weather GIS: Open-Meteo hourly numerical control points are interpolated into 15-minute visual steps.
- A 384-hour provider weather cube is requested for the live window.
- After the provider window, the timeline switches to daily COCOAID climate-conditioned modeled snapshots through 2050.
- The UI explicitly discloses that the 15-minute steps are interpolation between hourly numerical model controls, not native 15-minute provider observations.
- Long-range projections remain daily because sub-daily projection through 2050 would imply unsupported precision and create an unnecessarily large timeline.

## Hazard Intelligence / Extreme Weather Detection
- Rebuilt the page around one selected threat at a time.
- Preserved detected-period count, peak severity, total estimated production loss, maximum trees affected, full event list, date rail, and technical comparison chart.
- Added a selected-threat card with severity, loss, affected trees, confidence, source boundary, and impact summary.
- Added plain-language first farm action guidance based on the selected weather threat.
- The technical severity/loss graph is now collapsed by default to reduce cognitive load.

## Version
- Interface version: `phase11-agritech-interface-1.3.6`
- Design system version: `cocoaid-official-agritech-1.3.6`
