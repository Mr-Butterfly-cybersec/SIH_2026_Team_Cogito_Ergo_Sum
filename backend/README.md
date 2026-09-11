# CRQ Platform — Backend

FastAPI service for the SIH26105 cyber-risk quantification and investment
optimization platform.

## Setup

```bash
uv sync                 # create venv + install deps
uv run pytest           # run tests
uv run uvicorn app.main:app --reload
```

The API listens on `http://localhost:8000`:

- `GET /health` — liveness (no DB required)
- `GET /health/db` — readiness (checks Postgres)
- `GET /docs` — OpenAPI UI

Configuration comes from `../.env` (repo root) or `backend/.env`; see
`.env.example` at the repo root.
