# COCOAID Phase 11.3.13 — Farm Intelligence Runtime Fix

- Fixed the Analyze Farm Health null-element crash introduced when the Bayesian evidence and Suitability evidence cards were removed.
- Farm Health rendering now treats those removed UI mounts as optional instead of required.
- Pest-specific risk refresh is isolated so a Pest Risk request failure cannot prevent the Farm Health map, rehabilitation plan, calendar, donuts, and health charts from rendering.
- Bumped interface/cache version to 1.3.13 / 11.3.13.
