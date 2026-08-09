# COCOAID Phase 11.3.10 — Broadcast-Style Hazard Visual Refresh

## Summary
This release refines the Extreme Weather Detection workspace to visually resemble a weather-news broadcast panel while preserving interactive map behavior and farm-scale hazard interpretation.

## Key changes
- Reworked the **Selected Threat** visual into a broadcast-style weather panel.
- Added a **COCOAID WEATHER WATCH** top header and a lower-third bulletin banner.
- Added a stronger weather-map look with a dark satellite-style backdrop, hazard intensity field, red tracking box, and green reference grid.
- Added a dynamic event headline that updates with the selected hazard label and severity score.
- Kept the map interactive through Leaflet while presenting the overlay like a weather-news screen.
- Hardened the **Satellite** layer toggle with a more reliable primary imagery source and a NASA GIBS fallback.
- Preserved event-reactive Farm Health indicators and rehabilitation calendar behavior from Phase 11.3.9.

## Validation focus
- Satellite tile stacking and fallback path
- Hazard map headline, overlays, and event rendering
- Hazard calendar spacing and ping separation
- Rehabilitation map centering and calendar workflow
- Asset version bump to 11.3.10 / interface 1.3.10
