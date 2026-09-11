# Deployment (zero-budget split)

Target topology: **Vercel Hobby** (frontend) + **Neon Free** (Postgres) +
**Railway trial/Free** (API + cron).

## Database — Neon Free

- Create a project; copy the **pooled** connection string (`...-pooler...neon.tech`).
- App connection (pooled):
  `postgresql+asyncpg://<user>:<pw>@<host>-pooler.<region>.aws.neon.tech/<db>?ssl=require`
  → set as `DATABASE_URL`.
- Use a **direct** (non-pooled) connection for Alembic migrations and `pg_dump`.
- Notes: scale-to-zero after ~5 min idle (sub-second wake); pooled mode has no SQL-level
  `PREPARE`, no session `SET`, no `LISTEN/NOTIFY`.

## Backend — Railway

Two services from the same repo, both rooted at `backend/`:

1. **api** — copy `railway.api.json` to `backend/railway.json`.
2. **cron** — cron service, copy `railway.cron.json` to `backend/railway.json`
   (or configure the schedule in the dashboard). Runs `python -m app.jobs.ingest`
   every 6 hours and exits.

Set variables on the API service: `DATABASE_URL`, `CORS_ORIGINS` (the Vercel URL),
`ADMIN_SECRET`, `NVD_API_KEY`, `GROQ_API_KEY` (and optional fallbacks).

> **Gotchas:** Railway's Free plan ($1/mo credit) cannot host a 24/7 stack — use the
> $5/30-day trial or Hobby. The **Limited Trial blocks outbound network**, which silently
> breaks ingestion; verify your GitHub account at <https://railway.com/verify> for the
> Full Trial. Cron runs are **skipped if the previous run is still active** — the job has
> a hard timeout and exits cleanly.

## Frontend — Vercel Hobby

- Import the repo, set **Root Directory** to `frontend/`.
- `infra/vercel.json` provides the install/build commands (`npm install --include=dev`).
- Set `NEXT_PUBLIC_API_BASE_URL` to the Railway API public domain.
- Note: Vercel Hobby prohibits commercial use — fine for a hackathon demo.

## Local parity

`docker compose up --build` reproduces the same three tiers locally. See the root
`README.md` and `Makefile`.
