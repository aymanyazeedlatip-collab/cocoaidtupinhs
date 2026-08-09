# COCOAID v3 Phase 3: Weather Assimilation

This release implements a versioned weather assimilation boundary for the existing COCOAID research prototype.

- Contract API: `3.0.0-draft.3`
- Migration: `phase3_weather_assimilation`
- Weather engine: `v3.weather_assimilation` version `1.0.0`
- Feature adapter: `weather-features-1.0.0`
- Live numerical horizon: current conditions plus no more than 16 days

See `docs/phase_3/` for architecture, feature definitions, API details, failure behavior, test evidence, and user actions.
