# COCOAID Phase 11.3.15 — Rehabilitation Grid, Immediate Phase Workflow, and Hologram Polish

## Farm Health / Rehabilitation
- Replaced the fragile pane-level CSS clip used by the rehabilitation heatmap.
- Every rehabilitation grid cell is now geometrically intersected with the actual farm polygon before it is drawn.
- Interior cells remain square; boundary cells are cut to the farm outline.
- Grid-cell fill and border visibility were increased and the cells are directly interactive.

## Automatic Phase 9 and Phase 10
- Added `/api/v2/workflows/auto-phase9-10/bootstrap`.
- The farmer-facing Long-Term Forecast now calls the bootstrap immediately after a successful forecast is generated.
- The bridge creates a matching v3 weather-feature/production record for the same farm, then immediately queues the existing Phase 9/10 runner.
- This removes the mismatch where the UI created a legacy long-term forecast but the automatic runner only watched the v3 production repository.

## Interaction affordances
- Previous/next/calendar/rehabilitation arrow buttons now use orange glass surfaces, stronger borders, glow, hover scale, and active feedback so they are visibly clickable.

## CoCO-PILOT
- Retains the NCS-style holographic sphere.
- Upgraded to a larger glass-cockpit panel with layered green/cream glass, clearer chat bubbles, refined prompt chips, improved compose area, and stronger visual hierarchy.
- Sphere state animations remain tied to waiting, typing, loading, and speaking states.

## Mature coconut hologram
- The main coconut mesh is more spherical to represent a mature coconut.
- Coconut mesh depth colors changed from white to warm brown/copper holographic tones.
- The loading screen now starts on the same mature-brown coconut state instead of starting on the tree phase.
