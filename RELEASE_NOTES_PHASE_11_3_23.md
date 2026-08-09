# COCOAID Phase 11.3.23 — Deployment-Ready Final Build

This release converts the Phase 11.3.22 local research build into a production-deployment package while preserving all existing analytical and UI behavior.

## Deployment changes

- Added a Render production Blueprint with a single FastAPI instance in Singapore, a persistent disk, production environment flags, health checks, and automatic Git deploys.
- Added a production-only dependency list (`requirements.deploy.txt`) without pytest/respx development packages.
- Added `.python-version` for cloud runtime consistency.
- Added `scripts/start_production.sh` with single-worker execution and BLAS/OpenMP thread limits to reduce memory pressure.
- Added Vercel programmatic configuration (`vercel.mjs`) and `scripts/build_vercel_frontend.mjs` so Vercel publishes only the static frontend and proxies `/api/*` to the configured Render backend.
- Added `PERSISTENT_DATA_DIR`, which automatically relocates SQLite, reports, cache, assistant documents, and private assistant settings to mounted storage.
- Added a production server-side automatic Phase 9/10 fallback loop. Manual workflow UUID collection is not required.
- Added a production safety switch that disables browser-side Gemini API-key editing when `ALLOW_RUNTIME_API_KEY_CONFIGURATION=false`.
- Added `DEPLOYMENT_GUIDE.md`, `DEPLOYMENT_ENV.example`, and an optional `render.free-demo.yaml` reference.

## Validation

- 337 unit tests passed.
- 54 integration tests passed.
- 9 mathematical tests passed.
- 400 automated tests passed in total.
- Phase 3 through Phase 11 verification passed.
- Deployment verifier passed with a completely empty persistent data directory and automatically seeded 35-candidate intercrop catalog.
- Vercel frontend build and programmatic configuration checks passed.
