# COCOAID Phase 11.3.23 — Deployment Guide

This release is deployment-ready and no longer requires manual Phase 9/10 UUID collection.

## Recommended architecture

**Vercel = static frontend**  
**Render = FastAPI backend + ML models + SQLite + saved reports/uploads + automatic Phase 9/10**

The same repository is used for both services. The Vercel build automatically copies only `app/static/` into a deployment output folder and proxies `/api/*` requests to the Render backend.

A second supported option is **Render-only**, because the FastAPI application already serves the complete frontend at `/`.

Do not use Vercel-only for the full COCOAID backend in this release. COCOAID writes SQLite records, reports, assistant documents/cache, and can run long-lived automatic Phase 9/10 work. The production backend is configured for a normal Render web service with persistent disk storage and one process.

---

# A. First: put this build in GitHub

1. Extract the ZIP into a new empty folder.
2. Create a new GitHub repository, for example `COCOAID`.
3. Upload/push **everything from the ZIP root** to the repository root.
4. Make sure these files are visible at the repository root:
   - `render.yaml`
   - `vercel.mjs`
   - `.python-version`
   - `requirements.deploy.txt`
   - `app/`
   - `scripts/`
5. Push/commit to your main branch.

You do **not** run `setup.bat` on Render or Vercel. `setup.bat` remains for local Windows use only.

---

# B. Deploy the backend on Render first

## Recommended production configuration

The included `render.yaml` already defines the backend with:

- service name: `cocoaid-backend`
- runtime: Python
- region: Singapore
- plan: Standard
- one instance
- build command: `pip install --disable-pip-version-check --prefer-binary -r requirements.deploy.txt`
- start command: `bash scripts/start_production.sh`
- health check: `/api/health`
- persistent disk: 1 GB at `/var/data/cocoaid`
- automatic Phase 9/10 background checks enabled
- runtime Gemini-key editing disabled for production safety

### Render steps

1. Open Render.
2. Choose **New → Blueprint**.
3. Connect the GitHub repository containing this build.
4. Render should detect `render.yaml` automatically.
5. Review the service and create/sync the Blueprint.
6. Wait for the first build to finish.
7. Copy the public backend URL. It will look similar to:
   `https://cocoaid-backend.onrender.com`
8. Open:
   `https://YOUR-RENDER-URL/api/health`
9. A correct production deployment should return HTTP 200 and include:
   - `"status": "healthy"`
   - `"environment": "production"`
   - `"persistent_storage_configured": true`
   - `"auto_phase_workflows": true`

### Optional CoCO-PILOT Gemini key

If you want the live Gemini-backed assistant:

1. Render service → **Environment**.
2. Add:
   - Key: `GEMINI_API_KEY`
   - Value: your Gemini API key
3. Save and deploy.

Do **not** put the Gemini API key in Vercel. It belongs only on the backend.

## Render variables already supplied by `render.yaml`

You normally do not need to type these manually when using the Blueprint:

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `HOST` | `0.0.0.0` |
| `PERSISTENT_DATA_DIR` | `/var/data/cocoaid` |
| `AUTO_PHASE_WORKFLOWS` | `true` |
| `AUTO_PHASE_POLL_SECONDS` | `90` |
| `ALLOW_RUNTIME_API_KEY_CONFIGURATION` | `false` |
| `AUTO_SEED_REFERENCE_DATA` | `true` |
| `ENABLE_V2_CONTRACT_API` | `true` |
| `ENABLE_LEGACY_API` | `true` |
| `ENABLE_REQUEST_METRICS` | `true` |
| `STRICT_MODEL_RUNTIME_COMPATIBILITY` | `true` |
| `LOG_LEVEL` | `INFO` |
| `LOG_FORMAT` | `json` |
| `CORS_ORIGINS` | `*` |
| `WEATHER_CONNECT_TIMEOUT_SECONDS` | `20` |
| `WEATHER_READ_TIMEOUT_SECONDS` | `60` |
| `WEATHER_REQUEST_ATTEMPTS` | `2` |
| `WEATHER_DIRECT_CONNECTION_FALLBACK` | `true` |
| `WEATHER_USE_SYSTEM_TRUST_STORE` | `true` |
| `GEMINI_MODEL` | `gemini-flash-latest` |

Render provides `PORT` automatically. Do not hard-code it.

### If you only want a temporary free demo

`render.free-demo.yaml` is included as a reference configuration. It does **not** use a persistent disk. Saved farms, reports, uploaded assistant documents, and other runtime data can disappear after restart/redeploy, so it is not the recommended final deployment.

---

# C. Deploy the frontend on Vercel

Deploy Render first because Vercel needs the Render backend URL.

1. Open Vercel.
2. Choose **Add New → Project**.
3. Import the same GitHub repository.
4. Keep the repository root as the project root. Do **not** choose `app/static` as the Vercel Root Directory.
5. The included `vercel.mjs` supplies the build command and output directory automatically.
6. Open **Environment Variables**.
7. Add this variable:

| Variable | Value |
|---|---|
| `COCOAID_BACKEND_URL` | `https://YOUR-RENDER-SERVICE.onrender.com` |

Use the Render URL with `https://` and no extra path such as `/api`.

Recommended: apply the variable to **Production** and **Preview**.

8. Click **Deploy**.
9. Vercel automatically runs `scripts/build_vercel_frontend.mjs`.
10. That build copies the current COCOAID frontend into `vercel_dist/` and deploys only the static site.
11. `/api/*` requests are automatically rewritten to the Render backend. You do not edit `app.js`, collect IDs, or paste backend paths manually.

### Verify Vercel

After deployment:

1. Open the Vercel URL.
2. Enter COCOAID normally.
3. Open this address using your Vercel domain:
   `https://YOUR-VERCEL-DOMAIN/api/health`
4. It should return the Render health JSON through the Vercel proxy.
5. Run one farm forecast.
6. Open Decision Support / Reports after the forecast. Phase 9 and Phase 10 should begin automatically.

---

# D. Automatic workflow behavior

You no longer need to run Phase scripts manually or collect UUIDs.

When a farm forecast is generated:

1. The legacy long-term forecast completes.
2. COCOAID automatically creates the matching v3 farm identifier.
3. Weather assimilation creates the required feature-set identifier.
4. A v3 production forecast record is persisted automatically.
5. Phase 9 starts automatically and evaluates the complete intercrop catalog.
6. Phase 9 composes pest/intercropping/rehabilitation/decision-support records.
7. Phase 10 starts automatically for the resulting analysis run.
8. CoCO-PILOT grounding and formal report records are generated.
9. A server-side Render fallback checks every 90 seconds for any eligible forecast that did not finish.

You do not need to copy:
- farm UUIDs
- production forecast IDs
- pest observation IDs
- analysis run IDs
- decision-support IDs

The workflow discovers and creates them automatically.

---

# E. Updating the deployed system later

With Git deployment enabled:

1. Update the repository.
2. Commit/push to the deployment branch.
3. Render automatically rebuilds the backend.
4. Vercel automatically rebuilds the frontend.
5. The persistent Render disk keeps the SQLite database, reports, assistant documents/cache, and other runtime-written data across deployments.

Do not upload `.env` or real API keys to GitHub.

---

# F. Render-only alternative

If you do not need Vercel, you may stop after Section B.

The Render backend also serves the complete COCOAID interface at its root URL:

`https://YOUR-RENDER-SERVICE.onrender.com/`

This is the simplest architecture because there is only one service and no Vercel environment variable.

The Vercel + Render split is useful when you specifically want the frontend on Vercel while keeping the stateful Python backend on Render.

---

# G. Deployment files in this release

- `render.yaml` — recommended persistent Render production Blueprint
- `render.free-demo.yaml` — optional non-persistent demo reference
- `.python-version` — Render Python runtime selection
- `requirements.deploy.txt` — production dependencies only; test packages removed
- `scripts/start_production.sh` — memory-conscious one-worker production startup
- `vercel.mjs` — Vercel static-build and API proxy configuration
- `scripts/build_vercel_frontend.mjs` — automatically prepares the frontend for Vercel
- `DEPLOYMENT_ENV.example` — environment variable reference
- `scripts/verify_deployment.py` — offline deployment-readiness verifier

