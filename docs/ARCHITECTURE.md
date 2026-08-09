# Architecture

COCO-AID uses one FastAPI process serving JSON APIs and a static vanilla-JavaScript frontend. SQLite provides local storage. This minimizes setup and avoids Docker, Redis, PostgreSQL, and a separate frontend build.

## Main layers

1. **Frontend** — landing, farm setup, weekly outlook, hazards, health, reports, database, settings, embedded Weather GIS.
2. **API** — validation, provider adapters, farm CRUD, official-data profiles, simulation, reports, and storage endpoints.
3. **Official data** — processed PSA table 2E4EVCP1 with status/provenance and province/region/national fallback.
4. **Weather** — Open-Meteo cube/point adapters, RainViewer, NASA GIBS, GDACS, PAGASA reference, cache, cooldown, stale fallback.
5. **Climate** — compact SSP projection layer and stochastic annual/daily weather generation.
6. **Mathematics** — Bayes, Beta updating, suitability functions, state transitions, probability and utility calculations.
7. **Models** — development regression/classification artifacts with formula fallbacks and metadata.
8. **Simulation** — vectorized Monte Carlo farm states, hybrid weekly farm-site outlook, three-product allocation, hazard extraction, scenario comparison.
9. **GIS** — area/centroid checks, farm polygon handling, rehabilitation cells, map overlays.
10. **Reports/storage** — PDF, DOCX, SQLite farms, forecasts, analyses, and reports.

## Data flow

Farm input + official province profile + weather/climate scenario + intervention
→ Bayesian/ML/context calculations
→ Monte Carlo annual states and production
→ climate-conditioned daily allocation
→ weekly weather/production frames
→ synchronized maps/charts/hazards/health
→ saved forecast and PDF/DOCX report.

## Trust boundaries

- Official PSA records retain status metadata.
- Aggregate production is not converted directly into farm yield.
- Short-term numerical forecasts and long-term projections have distinct data modes.
- Uniform rehabilitation cells are used when no measured spatial layer exists.
- External provider failures are surfaced or served from clearly stale cached data.

## Phase 3 versioned weather boundary

The v3 weather path now separates provider access from downstream analytics:

```text
Provider/cache → normalization → immutable weather run → feature adapter → analytical engines
```

Migration 3 stores run metadata, long-form weather values, versioned feature sets, and feature derivations. Current/forecast values are limited to a 16-day live horizon; dates beyond that remain in the distinct climate-conditioned simulation layer. See `docs/phase_3/ARCHITECTURE.md`.


## Phase 4–5 production and posterior boundary

```text
Phase 3 weather features → Phase 4 retained ML prediction → Phase 5 Bayesian farm-state posterior
```

Phase 4 freezes the retained model feature order and keeps raw ML and variety-adjusted outputs separate. Phase 5 consumes the persisted forecast, propagates farm states with a seeded particle filter, and writes a distinct posterior layer. New evidence updates the Bayesian state but never retrains the machine-learning artifact. See `docs/phase_5/ARCHITECTURE.md`.
