# Phase 4 API

## Production

- `GET /api/v2/production/status`
- `POST /api/v2/production/forecast`
- `GET /api/v2/production/forecasts`
- `GET /api/v2/production/forecasts/{forecast_id}`
- `POST /api/v2/production/actuals`
- `GET /api/v2/production/forecasts/{forecast_id}/performance`

A production request requires a stored Phase 3 `weather_feature_set_id`. This enforces weather-run provenance and prevents unversioned weather values from being passed directly to the model.

## Sanitized intercropping assessment

- `GET /api/v2/data-foundation/intercrop-income-assessment`

The endpoint returns only aggregate crop and site profiles, quality findings, approved uses, and privacy status.

## Contract version

`3.0.0-draft.4`
