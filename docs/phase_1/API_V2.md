# Phase 1 Contract API

Base path: `/api/v2`

The Phase 1 API is additive. It does not remove or redirect any v2.11 route.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v2/health` | Contract API, model-runtime, and migration status |
| GET | `/api/v2/configuration` | Non-secret configuration and feature flags |
| GET | `/api/v2/contracts` | Contract catalog with schema hashes |
| GET | `/api/v2/contracts/{name}` | Full JSON Schema for one contract |
| POST | `/api/v2/contracts/{name}/validate` | Validate and normalize a proposed contract payload |
| GET | `/api/v2/engines` | Legacy and planned engine descriptors |
| GET | `/api/v2/engines/{engine_id}` | One engine descriptor |
| GET | `/api/v2/models` | Model artifacts, hashes, feature schemas, and runtime status |
| GET | `/api/v2/parameters` | Parameter-set descriptors and content hashes |
| GET | `/api/v2/units` | Unit catalog and canonical variable units |
| GET | `/api/v2/database/migrations` | Applied and pending migration versions |

## Error response

Expected application and contract failures use a stable structure while retaining the legacy `detail` field:

```json
{
  "detail": "Human-readable explanation",
  "code": "validation_error",
  "status": 422,
  "path": "/api/v2/contracts/WeatherModelRun/validate",
  "request_id": "correlation-id",
  "details": {}
}
```

Every response receives `X-Request-ID`. When enabled, responses also receive `X-Process-Time-Ms`.
