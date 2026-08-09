# Phase 5 Architecture: Bayesian Farm-State Simulator

Phase 5 adds the executable `v3.bayesian` engine. It consumes a persisted Phase 4 production forecast and its linked Phase 3 weather-feature snapshot. It does not retrain or modify the retained production model.

## Runtime flow

```text
Phase 4 production forecast
        +
Versioned weather and farm features
        +
Initial palm-state vector OR prior posterior
        +
Optional real observations
        ↓
Evidence reliability gate
        ↓
Sequential importance/resampling particle filter
        ↓
Monthly palm, soil-fertility, and soil-water propagation
        ↓
Posterior production distribution and farm-state intervals
        ↓
Versioned posterior, diagnostics, provenance, and production-layer linkage
```

## Farm-state vector

Each particle tracks seven mutually exclusive palm states:

- young;
- healthy bearing;
- aging;
- stressed;
- infested or diseased;
- rehabilitating;
- dead.

It also tracks soil-fertility and soil-water indices. Monthly transitions preserve the total number of planting positions. Replanting moves dead or vacant positions to the young state rather than creating palms outside the inventory.

## Module boundaries

- `app/bayesian/particle_filter.py`: priors, evidence assimilation, transitions, posterior summaries, and deterministic simulation.
- `app/bayesian/repository.py`: observations, runs, posteriors, parameters, and evidence-audit persistence.
- `app/engines/bayesian.py`: links weather, production, prior state, evidence, provenance, and persistence.
- `app/domain/bayesian.py`: strict Phase 5 request, evidence, posterior, and diagnostic contracts.
- `app/api/v2/routes.py`: public Phase 5 endpoints.

Particles are summarized rather than stored individually. The random seed, particle count, parameter version, model versions, and evidence records are stored so the analytical run remains reproducible.
