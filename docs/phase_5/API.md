# Phase 5 API

## Endpoints

```text
GET  /api/v2/bayesian/status
POST /api/v2/bayesian/observations
GET  /api/v2/bayesian/observations
POST /api/v2/bayesian/simulate
GET  /api/v2/bayesian/posteriors
GET  /api/v2/bayesian/posteriors/{posterior_id}
```

## First simulation

Create a Phase 3 weather feature set and Phase 4 production forecast first. Then submit an initial palm state:

```json
{
  "production_forecast_id": "PASTE-PRODUCTION-FORECAST-ID",
  "initial_state": {
    "young": 25,
    "healthy_bearing": 300,
    "aging": 40,
    "stressed": 20,
    "infested_or_diseased": 5,
    "rehabilitating": 10,
    "dead": 0,
    "soil_fertility_index": 0.65,
    "soil_water_index": 0.60
  },
  "baseline_state_date": "2026-08-03T08:00:00Z",
  "horizon_months": 12,
  "particle_count": 1000,
  "random_seed": 20260803,
  "intervention": "none",
  "evidence_observation_ids": [],
  "farm_data_version": "manual-farm-profile-1"
}
```

## Sequential simulation

For a later update, omit `initial_state` and supply the previous posterior:

```json
{
  "production_forecast_id": "PASTE-CURRENT-PRODUCTION-FORECAST-ID",
  "prior_posterior_id": "PASTE-PRIOR-POSTERIOR-ID",
  "baseline_state_date": "2027-08-03T08:00:00Z",
  "horizon_months": 12,
  "particle_count": 1000,
  "random_seed": 20270803,
  "intervention": "monitoring",
  "evidence_observation_ids": ["PASTE-OBSERVATION-ID"],
  "farm_data_version": "farm-profile-2"
}
```

The prior posterior and production forecast must belong to the same farm. Evidence must also belong to that farm and, when linked to a forecast, to the same forecast.
