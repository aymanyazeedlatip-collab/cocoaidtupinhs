# COCOAID Phase 11.3.23 — Zero-Cost Deployment Release

## Purpose

This deployment hotfix converts the Phase 11.3.23 deployment build from a paid Render persistent-disk architecture to a zero-cost architecture intended for research demos and hobby deployment:

- Vercel Hobby: static frontend
- Render Free: FastAPI, machine-learning, forecasting, Phase 9/10 workflow runner
- Supabase Free Storage: private durable snapshots of the existing SQLite research database plus generated reports and assistant document extracts

The validated SQLite repository and model contracts are preserved. No PostgreSQL rewrite was introduced.

## Automatic deployment behavior

- No manual Phase 9 or Phase 10 IDs are required.
- Forecast generation automatically bridges legacy farm input into the v3 repositories.
- Phase 9 runs all intercrop candidates automatically.
- Phase 10 starts automatically after Phase 9.
- The server-side workflow poller can continue the process even when the browser is closed while the Render service remains awake.
- On startup, the backend creates the private Supabase Storage bucket when needed and restores the latest SQLite snapshot before database migrations and reference seeding.
- Database writes wake the background snapshot synchronizer.
- Generated reports and assistant extracted-document text are synchronized separately and restored lazily after a cold start.

## Free Render blueprint

`render.yaml` now requests `plan: free`, uses no persistent disk, and stores ephemeral runtime files under `/tmp/cocoaid-runtime`.

Required user-supplied Render secrets:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`

Optional:

- `GEMINI_API_KEY` for live Gemini-backed CoCO-PILOT interactions. Automatic Phase 10 does not require it.

## Vercel

The Vercel build remains static-only. The only required Vercel environment variable is:

- `COCOAID_BACKEND_URL=https://YOUR-RENDER-SERVICE.onrender.com`

## Verification

- Unit tests: 345 passed
- Integration tests: 54 passed
- Mathematical tests: 9 passed
- Total automated tests: 408 passed
- Installation verifier: passed
- Phase 3 through Phase 11 verifiers: passed
- Zero-cost deployment verifier: passed
- Simulated private Supabase bucket creation: passed
- Simulated SQLite snapshot upload/delete/restore round trip: passed
- Manual Phase IDs required: false
