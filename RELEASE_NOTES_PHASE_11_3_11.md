# COCOAID Phase 11.3.11 — Hazard Readability, Farm Intelligence, and Pest Risk UI

## Hazard Intelligence
- Removed the broadcast/news-style weather map from the Selected Threat card.
- Replaced the removed map with a compact event-signature panel and period-level weather summary.
- Corrected contradictory event-weather displays by aggregating the entire flagged event window rather than reading only the first day.
- Added event weather evidence directly to saved extreme-event records: rainfall total, peak weekly rainfall, peak temperature, peak wind, wind direction, and mean humidity.
- Added semantic consistency guards so modeled Extreme Rain and Heat Stress labels require compatible generated weather conditions.
- Added four visual gauge cards for flagged periods, peak severity, production loss, and maximum trees affected.
- Removed the legacy event-list ping that overlapped dates.
- Enlarged dates, event names, severity badges, and metadata while increasing row spacing.

## Farm Intelligence
- Moved the rehabilitation calendar into a compact side rail.
- Enlarged the Leaflet rehabilitation map and made it the dominant page element.
- Kept the map and calendar visible side by side on desktop layouts.
- Preserved exact farm-bound centering and event-reactive health indicators.

## Pest Risk
- Added a richer agri-tech introductory card and evidence chips.
- Increased graph and card spacing, font sizes, line heights, and visual hierarchy.
- Changed detailed pest cards to a roomier three-column desktop layout.
- Improved risk-card front/back readability, photo area, driver chips, recommendations, and formulas.

## Release
- Interface version: `phase11-agritech-interface-1.3.11`
- Static asset cache version: `11.3.11`
