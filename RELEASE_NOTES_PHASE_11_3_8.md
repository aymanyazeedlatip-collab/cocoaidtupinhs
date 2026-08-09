# COCOAID Phase 11.3.8 Release Notes

## Scope
Phase 11.3.8 refines the farmer-facing forecast, hazard, farm-health, pest-risk, and loading experiences without changing the preserved analytical contracts. It builds directly on Phase 11.3.7 hourly provider forecasting.

## Long-Term Model Forecast
- Restored an always-visible range slider for rapid movement across the complete forecast horizon.
- Retained the interactive Calendar as an optional expanded view opened from the Calendar button.
- The first 16 days remain hourly Open-Meteo provider frames; post-provider frames remain daily climate-conditioned modeled snapshots.
- Converted Rain, Wind, Satellite, and Farm layer controls to switch-style on/off toggles.
- Fixed the forecast wind canvas being hidden by a legacy `#forecastWindCanvas { display:none !important; }` rule. The Phase 11 override now uses higher ID+class specificity so the Weather GIS-style wind overlay can render.
- Forecast wind uses the Weather GIS visual conventions for arrow geometry, particle density, opacity, shadow, movement, provider vector grids, and terrain deflection, with a uniform-vector fallback when a grid is unavailable.

## Extreme Weather Event Calendar
- Replaced the dense date rail with an interactive month calendar.
- Event dates use small status dots in a dedicated bottom zone, physically separate from the day number.
- Provider-backed, modeled, and severe-event dots use distinct colors with a compact legend.
- Selecting an event date updates the existing detailed hazard summary rather than discarding analytical detail.

## Farm Health Monitoring
- Reorganized Farm Health as a map-first workspace with the rehabilitation/condition map as the primary visual anchor.
- Added a consolidated farm-health scorecard chart while preserving tree-state, Bayesian evidence, suitability, priority-cell, and rehabilitation information.
- Kept Farm Health focused on whole-farm condition rather than mixing detailed pest rankings into the same screen.

## Dedicated Pest Risk workspace
- Added a new Pest Risk navigation tab.
- Moved pest-specific risk cards into that dedicated workspace.
- Added a highest-risk-first ranking visualization and a shared-driver visualization.
- Preserved the original pest-specific analytical outputs and recommendations.
- Weather GIS remains the final primary navigation item.

## Loading experience
- Replaced the white loading background with a semi-transparent green glass overlay.
- Added an animated miniature coconut-tree hologram beneath the spinning COCOAID logo.
- Added a 12-segment square progress indicator with accessible progressbar semantics.
- Loading status and supporting text use high-contrast orange tones.

## Version
- Interface version: `phase11-agritech-interface-1.3.8`
- Design system version: `cocoaid-official-agritech-1.3.8`
