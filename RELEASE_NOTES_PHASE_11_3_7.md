# COCOAID Phase 11.3.7 Release Notes

## Scope
Phase 11.3.7 is a focused Productivity / Long-Term Model Forecast refinement. It preserves the Phase 11.3.6 analytical contracts and Extreme Weather redesign while fixing forecast temporal presentation, wind parity, calendar navigation, full-viewport map coverage, and floating-panel collisions.

## Hourly provider forecast parity
- The genuine provider-backed forecast window now uses the original hourly Open-Meteo numerical-model control points.
- Long-Term Model Forecast requests the same 384-hour provider weather cube used by the dedicated Weather GIS and builds one visual frame per provider hour.
- Weather GIS Forecast mode was also standardized to one-hour playback so both interfaces advance through the provider horizon at the same temporal step.
- Provider dates and hour chips are grouped and displayed in the farmer's local browser time.
- After the provider horizon, COCOAID continues with daily climate-conditioned modeled snapshots through 2050.
- The modeled period remains daily; it is not presented with artificial hourly or sub-hourly precision decades into the future.

## Full-screen forecast workspace
- Forced the Productivity forecast workspace and Leaflet map to the complete viewport with no intentional side gutters.
- Summary, Layers, Graphs, and Timeline start collapsed so the farmer begins with an unobstructed map.
- Opening a side drawer closes the Timeline; opening the Timeline closes every side drawer.
- Added explicit desktop, tablet, and mobile collision-safe lanes for the title, Refresh Forecast action, tool rail, side drawers, and calendar.
- The title and Refresh Forecast action use separate mobile layout columns instead of overlapping element boxes.
- The unrelated floating Weather GIS and CoCO-PILOT shortcuts remain hidden while the full-screen Productivity map is active.

## Liquid-glass floating controls
- Forecast title, tool buttons, side drawers, legend, and Timeline use a semi-transparent white glass base with blur, subtle border, and restrained shadow.
- Increased forecast labels, panel headings, layer descriptions, metrics, and map-control text for better legibility.
- Side drawers use larger spacing and readable card sizing instead of the previous compressed layout.

## Interactive calendar timeline
- Replaced the visible range-slider timeline with an interactive month calendar.
- Calendar days indicate provider-backed versus modeled dates using separate small status dots positioned away from the date number.
- Selecting a provider-backed day exposes its available hourly frames in a horizontal hour picker.
- Selecting a modeled day switches the UI to one daily modeled snapshot.
- Previous/next month controls are bounded to the available forecast horizon.
- The legacy range element remains hidden only for backward compatibility with existing code paths.

## Weather GIS wind parity
- Removed the separate simplified wind implementation from the Productivity map.
- Productivity now uses the Weather GIS particle/arrow conventions for vector interpolation, terrain-aware deflection, particle density, arrow geometry, opacity, and animation movement.
- The wind canvas remains an independent semi-transparent overlay above Leaflet and follows the current provider grid when available.

## Version
- Interface version: `phase11-agritech-interface-1.3.7`
- Design system version: `cocoaid-official-agritech-1.3.7`
