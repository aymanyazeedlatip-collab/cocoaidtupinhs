# Phase 10 API

```text
GET  /api/v2/coco-pilot/status
POST /api/v2/coco-pilot/explain
GET  /api/v2/coco-pilot/runs
GET  /api/v2/coco-pilot/runs/{run_id}
POST /api/v2/formal-reports/generate
GET  /api/v2/formal-reports
GET  /api/v2/formal-reports/{report_id}
GET  /api/v2/formal-reports/{report_id}/download
```

The default provider is deterministic. `gemini_if_configured` is optional and never blocks formal report generation.
