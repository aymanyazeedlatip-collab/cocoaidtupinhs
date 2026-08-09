# COCO-AID v2.2.1 — Forecast Bug Fix and Terrain-Aware Wind Arrows

## Fixed

- Resolved repeated HTTP 422 failures when Run Forecast received an empty, stale, or legacy run-count value.
- Added clear field-level error messages instead of object-string error output.
- Added safe numeric defaults for legacy or blank farm inputs.
- Prevented repeated forecast POST requests while one request is in progress.

## Wind visualization

- Wind is rendered as moving arrows rather than short dot-like traces.
- The live Weather GIS samples the forecast-grid elevation returned by Open-Meteo and applies a bounded terrain-deflection model to the arrow field.
- The long-term outlook applies a local elevation-and-slope deflection proxy around the farm site.
- The terrain adjustment is a map visualization approximation, not computational fluid dynamics.

## Compatibility

- Supports 100, 500, 1,000, 2,000, and 5,000 Monte Carlo runs.
- Existing v2.2 saved settings are normalized automatically.
