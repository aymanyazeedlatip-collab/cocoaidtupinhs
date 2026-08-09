# Phase 7 API

- `GET /api/v2/intercropping/status`
- `GET /api/v2/intercropping/candidates`
- `POST /api/v2/intercropping/assess`
- `GET /api/v2/intercropping/assessments`
- `GET /api/v2/intercropping/assessments/{assessment_id}`

The assessment endpoint requires a saved Phase 4 production forecast. A Phase 6 pest run is optional but required to condition crop-specific pest conflicts on current inferred risks.
