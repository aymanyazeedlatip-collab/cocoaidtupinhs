# COCOAID Zero-Cost Deployment Guide

This build is configured specifically for a **₱0 / $0 hosting setup** using:

- **Vercel Hobby** for the static frontend.
- **Render Free** for the FastAPI/ML backend.
- **Supabase Free** for durable private state storage.

No paid Render instance and no Render persistent disk are used anywhere in this build.

## Architecture

```text
Browser
  |
  v
Vercel Hobby (static COCOAID frontend)
  |
  | /api/* rewrite
  v
Render Free (FastAPI + ML + simulation + Phase 9/10 automation)
  |
  | private server-side sync
  v
Supabase Free Storage
  |- state/coco_aid.sqlite3
  |- reports/*
  `- assistant_documents/*
```

COCOAID continues to use its existing SQLite research repository internally. Render Free's filesystem is temporary, so the backend automatically keeps a consistent SQLite snapshot in a **private Supabase Storage bucket**. On a cold start it downloads the last snapshot before running migrations and reference-data seeding.

This preserves the existing Phase 1-10 repository behavior and avoids a risky database-engine rewrite solely for free hosting.

## What is automatic in this build

You do **not** create a Supabase table, database schema, storage bucket, Phase ID, farm UUID, forecast UUID, analysis ID, or report directory manually.

At startup COCOAID automatically:

1. Validates the two Supabase server credentials.
2. Creates the private `cocoaid-state` Storage bucket if it does not already exist.
3. Downloads the most recent SQLite snapshot when one exists.
4. Runs all local database migrations.
5. Seeds the reference catalogs when required.
6. Uploads the initialized database on a first deployment.
7. Keeps the database synchronized after writes and periodically while the service is running.
8. Stores generated PDF/DOCX reports in Supabase and restores them lazily after cold starts.
9. Stores extracted CoCO-PILOT document attachments in Supabase and restores them lazily.
10. Automatically runs the Phase 9 -> Phase 10 bridge after a farm forecast.

## Important free-tier behavior

The application is intentionally configured for research/demo use on free hosting.

- Render Free can spin down after inactivity. The first request after a spin-down can therefore take noticeably longer.
- Render Free has no persistent disk. This build handles that by synchronizing state to Supabase.
- Supabase Free can pause an inactive project. If that happens, open Supabase and click **Resume project**.
- Vercel Hobby is intended for personal/non-commercial projects.
- Do not upgrade any of these services if your requirement is zero cost.

---

# Part 1 - Upload the final build to GitHub

Extract the final ZIP into an empty folder. The folder should directly contain files such as:

```text
app/
scripts/
render.yaml
vercel.mjs
requirements.deploy.txt
DEPLOYMENT_GUIDE.md
```

Open CMD in that folder and run:

```cmd
git init
git add .
git commit -m "COCOAID zero-cost deployment build"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

If `origin` already exists:

```cmd
git remote set-url origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git add .
git commit -m "COCOAID zero-cost deployment build"
git push -u origin main
```

---

# Part 2 - Create the Supabase Free project

Create this **before Render** because Render needs two Supabase values.

1. Sign in to Supabase.
2. Create a new project under a **Free** organization.
3. Do not select or upgrade to Pro.
4. Give the project any name, for example `cocoaid-state`.
5. Set a database password and save it somewhere safe. **COCOAID does not need this password for this deployment.**
6. Wait until the project finishes provisioning.

## Get `SUPABASE_URL`

Open the project and use the **Connect** dialog or Project Settings to copy the project URL. It looks like:

```text
https://abcdefghijk.supabase.co
```

This becomes:

```text
SUPABASE_URL
```

## Get `SUPABASE_SECRET_KEY`

Open:

**Project Settings -> API Keys**

Use the server-side **Secret key** that starts with:

```text
sb_secret_
```

If the project only shows the older key system, you can create the new Publishable/Secret keys from that page. The server-side Secret key is the one COCOAID needs.

Do **not** use the Publishable key for the backend state store.

Do **not** put the Secret key in Vercel or in GitHub.

### You do NOT need to create a Supabase bucket manually

COCOAID automatically creates a private bucket called:

```text
cocoaid-state
```

on its first successful backend startup.

You also do not need to run SQL in Supabase.

---

# Part 3 - Deploy the backend on Render Free

If you previously started creating the paid `cocoaid-backend` Blueprint, you can delete that failed service/Blueprint first. This build uses the new name:

```text
cocoaid-backend-free
```

## Create the Blueprint

1. Sign in to Render.
2. Click **New**.
3. Choose **Blueprint**.
4. Connect the GitHub repository containing this final build.
5. Render should detect `render.yaml` automatically.
6. Confirm that the service is shown as **Free**.
7. Confirm that there is **no persistent disk** listed.

The included `render.yaml` explicitly contains:

```yaml
plan: free
```

and contains no `disk:` block.

## Required Render secret values

Because the Blueprint marks these values as `sync: false`, Render will ask you to supply them:

### `SUPABASE_URL`

Example:

```text
https://abcdefghijk.supabase.co
```

### `SUPABASE_SECRET_KEY`

Example format:

```text
sb_secret_xxxxxxxxxxxxxxxxx
```

These two values belong **only on Render**.

## Render variables already configured automatically

You should not need to manually enter these because `render.yaml` already declares them:

```text
ENVIRONMENT=production
HOST=0.0.0.0
PERSISTENT_DATA_DIR=/tmp/cocoaid-runtime
AUTO_PHASE_WORKFLOWS=true
AUTO_PHASE_POLL_SECONDS=90
ALLOW_RUNTIME_API_KEY_CONFIGURATION=false
AUTO_SEED_REFERENCE_DATA=true
ENABLE_V2_CONTRACT_API=true
ENABLE_LEGACY_API=true
ENABLE_REQUEST_METRICS=true
STRICT_MODEL_RUNTIME_COMPATIBILITY=true
LOG_LEVEL=INFO
LOG_FORMAT=json
CORS_ORIGINS=*
SUPABASE_STATE_SYNC_ENABLED=true
SUPABASE_STATE_REQUIRED=true
SUPABASE_STORAGE_BUCKET=cocoaid-state
SUPABASE_STATE_OBJECT=state/coco_aid.sqlite3
SUPABASE_STATE_SYNC_SECONDS=10
SUPABASE_STATE_TIMEOUT_SECONDS=20
WEATHER_CONNECT_TIMEOUT_SECONDS=20
WEATHER_READ_TIMEOUT_SECONDS=60
WEATHER_REQUEST_ATTEMPTS=2
WEATHER_DIRECT_CONNECTION_FALLBACK=true
WEATHER_USE_SYSTEM_TRUST_STORE=true
GEMINI_MODEL=gemini-flash-latest
```

## Gemini is optional

For the strictest zero-cost deployment, **do not add `GEMINI_API_KEY` unless you already know your Gemini API account/key has a free quota that you want to use**.

Without `GEMINI_API_KEY`, the rest of COCOAID still runs. The live Gemini-backed CoCO-PILOT chat is simply not configured.

If you intentionally want Gemini later, add this to Render only:

```text
GEMINI_API_KEY=your_key
```

Never place Gemini or Supabase secret keys in Vercel frontend variables.

## Deploy

Finish creating the Blueprint and wait for the build.

After Render reports the service as live, copy the backend URL. It should look similar to:

```text
https://cocoaid-backend-free.onrender.com
```

Open:

```text
https://YOUR-RENDER-URL/api/health
```

A healthy free deployment should report values similar to:

```json
{
  "status": "healthy",
  "environment": "production",
  "persistent_storage_configured": true,
  "storage_mode": "supabase_storage",
  "auto_phase_workflows": true,
  "supabase_state": {
    "enabled": true,
    "configured": true,
    "required": true,
    "bucket": "cocoaid-state",
    "last_error": null
  }
}
```

If `configured` is false, recheck the two Supabase values in Render.

If Supabase is paused, resume the Supabase project and redeploy/restart Render.

---

# Part 4 - Deploy the frontend on Vercel Hobby

Only do this after the Render backend is live.

1. Sign in to Vercel using your personal account.
2. Stay on the **Hobby** plan.
3. Click **Add New -> Project**.
4. Import the same GitHub repository.
5. Keep **Root Directory** at the repository root.
6. Do not change the build command manually unless Vercel fails to read `vercel.mjs`.

The build automatically copies only the frontend assets into `vercel_dist`.

## The only Vercel environment variable

Open:

**Project -> Settings -> Environment Variables**

Create:

```text
COCOAID_BACKEND_URL
```

Set it to the exact Render backend origin, for example:

```text
https://cocoaid-backend-free.onrender.com
```

Do not include a trailing `/api`.

Apply it to **Production**. You can also apply it to Preview if you want preview deployments to use the same backend.

You do **not** put any of these on Vercel:

```text
SUPABASE_SECRET_KEY
GEMINI_API_KEY
```

Those are server secrets.

Deploy the Vercel project.

---

# Part 5 - Final checks

Assume your Vercel site is:

```text
https://your-cocoaid-project.vercel.app
```

## Check the frontend

Open:

```text
https://your-cocoaid-project.vercel.app
```

The COCOAID landing page should load normally.

## Check the Vercel -> Render API bridge

Open:

```text
https://your-cocoaid-project.vercel.app/api/health
```

You should see the same health response returned by Render.

## Check Supabase persistence

1. Use COCOAID to save a farm or produce an analysis.
2. Wait roughly 10-20 seconds.
3. Open Supabase -> Storage.
4. A private bucket named `cocoaid-state` should now exist automatically.
5. It should contain a database object at:

```text
state/coco_aid.sqlite3
```

Generated reports appear under:

```text
reports/
```

Do not make this bucket public.

## Verify a cold start

After Render has been inactive long enough to spin down, open the site again. Render may take longer to wake. Once it is running, previously saved farm/database state should be restored from Supabase automatically.

---

# Updating the deployed system later

After you change local project files:

```cmd
git add .
git commit -m "Update COCOAID"
git push
```

Render and Vercel will redeploy from GitHub automatically.

The SQLite state itself is not committed to GitHub. The deployed runtime state remains in the private Supabase bucket.

---

# How to make sure you never intentionally select a paid resource

For the strictest zero-charge setup, **do not add a payment method to Render**. Render documents that when a Free workspace without a payment method exceeds billable included bandwidth/build limits, Render suspends the affected free services/builds instead of charging the account. If you already attached a card to the workspace and you require a hard zero-cost ceiling, remove the payment method before continuing when the dashboard permits it.

Likewise, remain on Vercel Hobby and Supabase Free and do not accept an upgrade/trial that requests billing details.

Use only these options:

```text
Vercel: Hobby
Render web service: Free
Render persistent disk: NONE
Render Postgres: NONE
Supabase organization/project: Free
```

If a dashboard shows **Standard**, **Starter paid**, **Pro**, a persistent disk, or a monthly price, do not continue with that selection.

This repository's `render.yaml` is intentionally configured with `plan: free` and no disk, so the source configuration itself does not request a paid Render resource.

---

# Free-tier limitations to expect

The zero-cost deployment is appropriate for a school/research demonstration, but it is not equivalent to paid production hosting.

- Render Free can spin down after 15 minutes without inbound traffic and can take roughly a minute to wake again.
- Render Free provides 750 free instance hours per workspace per calendar month and has an ephemeral local filesystem.
- Supabase Free currently includes up to 1 GB of file storage. COCOAID caps an individual remote state object below the Free project's 50 MB maximum file limit.
- Supabase Free projects can be paused after insufficient activity over about a week; they can be resumed from the dashboard.
- Vercel Hobby is $0 and is intended for personal/non-commercial use. When included Hobby usage is exhausted, service/features can pause rather than silently converting this project into the paid COCOAID configuration.

Official references used while preparing this deployment build:

```text
https://render.com/docs/free
https://render.com/docs/blueprint-spec
https://supabase.com/pricing
https://supabase.com/docs/guides/storage/pricing
https://supabase.com/docs/guides/storage/uploads/file-limits
https://supabase.com/docs/guides/platform/free-project-pausing
https://supabase.com/docs/guides/getting-started/api-keys
https://vercel.com/docs/plans/hobby
```
