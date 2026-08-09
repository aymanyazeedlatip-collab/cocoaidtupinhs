# Phase 3 Weather API

Interactive documentation: `/docs`

## Status

`GET /api/v2/weather/status`

Returns engine version, 16-day boundary, feature-adapter version, storage counts, and conceptual boundaries.

## Assimilate

`POST /api/v2/weather/assimilate`

Example body:

```json
{
  "latitude": 6.334,
  "longitude": 124.952,
  "model": "auto",
  "forecast_days": 16,
  "history_days": 90,
  "force_refresh": false
}
```

The response contains:

- Stored weather run metadata
- Agricultural feature set
- Reuse/deduplication status
- Live-only current/16-day payload
- A separation notice

## Stored runs

- `GET /api/v2/weather/runs`
- `GET /api/v2/weather/runs/{run_id}`
- `GET /api/v2/weather/runs/{run_id}/features`

`include_values=true` may be used when retrieving a run. `period_kind` can filter to `historical`, `current`, or `forecast`.

## Run comparison

`GET /api/v2/weather/compare?base_run_id=...&comparison_run_id=...`

Only runs for the same location can be compared. The endpoint reports shared valid-date changes in precipitation, temperature, gust, and ET0 values.
