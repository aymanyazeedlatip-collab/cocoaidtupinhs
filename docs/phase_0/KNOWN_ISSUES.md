# Phase 0 Known-Issue Register

## Critical migration risks

### KI-001: Model serialization version mismatch

The bundled scikit-learn artifacts report serialization under version 1.9.0, while the audit environment has 1.8.0. Loading succeeds and tests pass, but scikit-learn emits compatibility warnings. Phase 1 must pin or recreate a compatible inference environment before model outputs are treated as reproducible releases.

### KI-002: Prototype model evidence limits

The production, pest, and suitability cards state that the models were trained on synthetic/reference-based development data. Their metrics describe performance against that constructed dataset, not independent farm validation. The UI and reports must not imply PCA validation or real-world accuracy.

### KI-003: Monolithic frontend

`app/static/app.js` is 2,808 lines and `app/static/styles.css` is 3,464 lines. State, rendering, API calls, maps, charting, and domain-specific presentation are tightly coupled. New intercropping and Bayesian interfaces must not be appended directly to these files without feature boundaries.

### KI-004: Monolithic API orchestration

`app/api/routes.py` contains most API handlers in one module. It combines storage, live providers, analytical services, assistant operations, file uploads, and report generation. The v3 API must be split by bounded context while preserving legacy route compatibility.

### KI-005: JSON-blob persistence

The principal SQLite tables store entire requests and results as JSON text. This blocks normalized observation histories, parameter provenance, weather-run lineage, model-version joins, farmer-to-parcel relationships, and efficient geospatial queries.

### KI-006: Forecast semantics are mixed

The current application combines deterministic short-term weather with climate-conditioned long-term daily frames. The v3 system must visibly and structurally separate observation, numerical forecast, historical reconstruction, and stochastic climate simulation.

### KI-007: Simulated evidence can be mistaken for observed evidence

The existing stochastic state model and pest calculations are useful prototype components, but the v3 Bayesian update layer must enforce evidence status. Predicted or simulated outbreaks cannot update posterior beliefs as if they were confirmed field observations.

### KI-008: Pest taxonomy requires reconciliation

The PCA bundle includes Asiatic palm weevil guidance while the legacy system contains broader or different pest names. Labels, scientific identity, host behavior, and management guidance must be reviewed before combining rules.

### KI-009: Farmer registry contains PII and structural anomalies

The workbook contains names and multiple data-quality flags. It must remain in restricted raw staging. Duplicate detection and anomaly flags require review workflows rather than destructive cleanup.

## Secondary engineering risks

- Live point weather currently requests 10 forecast days, while gridded weather is capped at 120 hours. The revised 16-day product contract requires a new provider and storage design.
- Weather and external assistant services introduce rate-limit, availability, and privacy dependencies.
- Current database migrations are implemented as inline `CREATE TABLE` and conditional `ALTER TABLE` statements rather than a formal migration framework.
- Model prediction functions return formula fallbacks or `None` on artifact errors; v3 must expose explicit engine status rather than silently degrading analytical claims.
- The supplied SQLite baseline is empty, so migration correctness must also be tested against synthetic populated legacy databases.
- Generated PDF/DOCX reports are integration-tested, but exact analytical report reproducibility requires immutable data and parameter lineage.
