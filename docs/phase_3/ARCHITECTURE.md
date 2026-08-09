# Phase 3 Weather Assimilation Architecture

Phase 3 introduces a versioned weather boundary between external forecast providers and all downstream COCOAID analytical engines. The legacy Weather GIS remains available, but provider payloads now pass through a normalized, persisted, and provenance-aware assimilation layer.

## Processing path

```text
Open-Meteo point forecast
        ↓
Provider adapter and cache
        ↓
Raw payload normalization
        ├── historical reference values
        ├── current values
        └── forecast values, maximum 16 days
        ↓
Versioned weather-model run and weather values
        ↓
Agricultural weather feature adapter
        ↓
Versioned feature set for the retained production model and later engines
```

## Module boundaries

- `app/weather/providers.py`: external API access, memory/disk cache, cooldown, stale fallback, offline behavior.
- `app/weather/assimilation/normalizer.py`: canonical time, unit, period-kind, horizon, and quality handling.
- `app/weather/assimilation/features.py`: lagged and forecast agricultural feature generation.
- `app/weather/assimilation/repository.py`: SQLite storage, retrieval, deduplication, and run comparison.
- `app/weather/assimilation/service.py`: orchestration used by the API and legacy point-weather endpoint.
- `app/engines/weather_assimilation.py`: executable v3 analytical-engine boundary.
- `app/api/v2/routes.py`: read-only status/run endpoints and explicit assimilation endpoint.

## Scientific boundaries

1. Live Weather GIS contains current conditions and forecast Days 1–16 only.
2. Provider `past_days` values are marked `reference_only`; they are not represented as measured station observations.
3. Conditions beyond Day 16 remain in Climate-Conditioned Farm Simulation.
4. A weather refresh creates a new prediction input. It does not retrain the retained ML model.
5. Missing or stale data are disclosed through quality flags and metadata rather than silently replaced.
