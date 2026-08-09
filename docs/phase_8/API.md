# Phase 8 API

- `GET /api/v2/rehabilitation/status`
- `POST /api/v2/rehabilitation/plan`
- `GET /api/v2/rehabilitation/plans`
- `GET /api/v2/rehabilitation/plans/{plan_id}`

The planning endpoint requires an existing Phase 4 production forecast. Phase 5, 6, and 7 IDs are optional, but omitting them reduces evidence coverage and is disclosed in warnings.
