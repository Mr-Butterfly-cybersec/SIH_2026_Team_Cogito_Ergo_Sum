# Cyber Risk Decision Engine — SIH26105

**AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform**
(AICTE Cyber Security Cell, SIH26105) · Team *Cogito Ergo Sum*

> From CVE to ₹ impact to optimal security spend.

It is not a security dashboard. It is a **risk-decision layer** over existing security tooling: it
converts technical evidence and business context into an uncertainty-aware financial loss
distribution, then chooses the security investments that remove the most modelled risk under a
fixed budget — and explains why.

**Status:** Phases 0–9 complete. 303 backend tests pass; the full stack runs locally via Docker.

| Phase | Area | State |
|---|---|---|
| 0 | Scaffold (this repo) | ✅ |
| 1 | Scientific core — Beta-PERT, Monte Carlo, provenance | ✅ |
| 2 | Evidence ingestion — NVD, EPSS, KEV, ATT&CK | ✅ |
| 3 | Business context + demo organization | ✅ |
| 4 | Investment optimizer (CP-SAT + baselines) | ✅ |
| 5 | Scenario engine + REST API | ✅ |
| 6 | Dashboard (Next.js + ECharts) | ✅ |
| 7 | Compliance mapping — 7 frameworks, priced gaps | ✅ |
| 8 | AI layer — tool-calling + grounding check | ✅ |
| 9 | Proof, polish, deployment | ✅ |

## Quickstart

```bash
cp .env.example .env          # optional; defaults work locally
make up                       # build + start Postgres, API, web
make migrate                  # create the schema (Alembic)
make seed                     # load the demo organization (33 assets, 11 controls)
#  API  http://localhost:8000/health
#  Docs http://localhost:8000/docs
#  Web  http://localhost:3000
make down                     # stop
```

Local development (no Docker for the app):

```bash
make install                  # uv sync + npm install
docker compose up -d db       # just the database
make dev-api                  # FastAPI on :8000 (reload)
make dev-web                  # Next.js on :3000
```

Requirements: Docker (+ compose), Python 3.12 via [uv](https://docs.astral.sh/uv/), Node 22+.

## Tests

```bash
make test                     # backend suite → 303 passed
make lint                     # ruff check + format check
cd frontend && npm run lint && npm run build
```

The backend suite is **fully offline** — mocked HTTP transports and committed fixtures. It needs no
API keys and no network, so a failure is always reproducible locally. It includes
`backend/tests/test_fuzz.py`, 44 property-based tests over the engine and the HTTP surface; they
have found four real defects that the example suite missed.

## Layout

```
backend/    FastAPI + SQLAlchemy + NumPy/SciPy/OR-Tools   (see backend/README.md)
frontend/   Next.js 16 + Tailwind v4 + ECharts            (see frontend/README.md)
docs/       architecture, methodology, research, API and the decision record
infra/      deployment config (Railway, Vercel)
```

## How it works (short version)

```
NVD/CVSS + EPSS + KEV  →  asset + business context  →  control effectiveness
        →  FAIR-inspired scenarios  →  Monte Carlo  →  EAL / P90 / P95 / P99
        →  what-if scenarios  →  budget optimizer  →  decision  →  framework mapping
```

Every number carries provenance (`PUBLIC_DATA`, `OBSERVED_TELEMETRY`, `USER_INPUT`,
`MODEL_ESTIMATE`, `SYNTHETIC_DEMO`) and simulations are reproducible from a stored seed.

Three rules keep it honest:

1. **No number originates in the LLM.** It selects a tool, the engine computes, and the model
   explains. Every figure is traceable to the engine — and the model still rounds and converts for
   readability, so the claim is about *origin*, not about never doing arithmetic.
2. **Synthetic demo assumptions are always labelled** as such.
3. **The optimiser is scored by re-simulation**, never by its own objective — and the benchmark
   fails loudly if it ever appears to beat the exact optimum, because that would mean the answer
   is invalid rather than good.

## API

All analytical endpoints live under `/api/v1` (interactive docs at `/docs`). Read endpoints serve
the same planning context the engine computes on, so displayed figures match the model.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/health/db` | liveness / readiness |
| GET | `/api/v1/overview` | posture (EAL/P90/P95), counts, criticality mix, evidence confidence |
| GET | `/api/v1/assets`, `/assets/{id}` | asset estate with criticality; detail adds findings + scenarios |
| GET | `/api/v1/findings` | findings joined with NVD/EPSS/KEV intelligence |
| GET | `/api/v1/controls` | control evidence, effectiveness, and the FAIR factor it moves |
| GET | `/api/v1/scenarios`, `/scenarios/{id}` | scenario catalogue; detail includes parameter provenance |
| GET | `/api/v1/candidates` | investment candidates (cost, prerequisites, impact) |
| POST | `/api/v1/scenarios/{id}/simulate` | Monte Carlo for one scenario, optionally hardened |
| POST | `/api/v1/portfolio/simulate` | re-simulate the whole estate with a selection applied |
| POST | `/api/v1/optimize` | budget → recommended portfolio + baseline comparison |
| POST | `/api/v1/what-if/scenarios/{id}/delay` | cost of postponing remediation N days |
| POST | `/api/v1/what-if/scenarios/{id}/criticality` | asset becomes more critical |
| POST | `/api/v1/what-if/scenarios/{id}/controls` | deploy a set of controls |
| GET | `/api/v1/compliance` | coverage + gaps across all seven frameworks |
| GET | `/api/v1/compliance/frameworks[/{id}]` | framework registry / single-framework coverage |
| GET | `/api/v1/compliance/requirements` | the internal control ontology |
| GET | `/api/v1/compliance/gaps` | open gaps, priced in rupees |
| POST | `/api/v1/ask` | natural-language question → grounded, engine-backed answer |
| GET | `/api/v1/ai/tools`, `/ai/status` | tool registry, provider chain and reachability |

Simulation responses return **binned histograms, percentiles and exceedance curves — never the raw
path array** — plus the seed, trial count, model version and evidence mix of the run.

```bash
curl -s localhost:8000/api/v1/overview | jq .posture
curl -s -X POST localhost:8000/api/v1/optimize \
  -H 'content-type: application/json' \
  -d '{"budget": 2500000, "n_trials": 20000}' | jq '.result, .comparison[].label'
```

## Dashboard

A **single decision page** — no screen navigation. Top to bottom:

1. **Executive briefing** — EAL, P90, P95 (VaR) and the evidence-confidence band, plus a sentence
   naming the single largest exposure. The decision before the evidence.
2. **Scenario explorer** — every scenario ranked by rupee exposure; select one to open it in place:
   EAL/P90/P95/CVaR, the loss-exceedance curve and annual-loss distribution, the controls that map
   to it, and live before→after deltas as you toggle them. Below: **cost of delaying remediation**
   and a **criticality stress test**.
3. **Investment optimizer** — set the budget, and compare the recommended portfolio against the
   naive baselines, all re-simulated on the same harness.
4. **Framework alignment** — one internal control ontology mapped to seven frameworks, gaps ranked
   by the rupee exposure they relate to.
5. **Ask the engine** — natural-language questions, with the tool calls behind each answer shown so
   the figure can be traced to the engine.
6. **Data confidence & assumptions** — where every input came from, and the run fingerprint.

Money is shown in Indian short scale (₹5.65 Cr / ₹56.5 L). Keyboard: **1–6** jumps between
sections, **/** focuses the question box.

## Documentation

**Start here**

- [`docs/architecture-decisions.md`](docs/architecture-decisions.md) — **why** the system is built
  this way: the decisions, their reasoning, and their costs. Best first read.
- [`docs/architecture.md`](docs/architecture.md) — components, data model, deployment topology
- [`docs/TECHNICAL.md`](docs/TECHNICAL.md) — the full technical picture, end to end

**Method and evidence**

- [`docs/methodology.md`](docs/methodology.md) — the FAIR model, formulas, optimiser (canonical)
- [`docs/TECHNICAL-EXPLAINED.md`](docs/TECHNICAL-EXPLAINED.md) — every formula and term, with a glossary
- [`docs/benchmark.md`](docs/benchmark.md) — optimiser vs baselines, generated by `make benchmark`
- [`docs/research.md`](docs/research.md) — research grounding, standards, empirical findings
- [`docs/references.md`](docs/references.md) — every source, tagged Used / Design / Context
- [`docs/sih26105-research-and-project-path.md`](docs/sih26105-research-and-project-path.md) — the original feasibility study and full bibliography

**Subsystems**

- [`docs/data-management-and-database.md`](docs/data-management-and-database.md) — ingestion, schema, provenance
- [`docs/ml-and-ai.md`](docs/ml-and-ai.md) — what is and is not machine learning here, and why
- [`docs/ui-and-ux.md`](docs/ui-and-ux.md) — dashboard panels, reading order, UX decisions
- [`docs/data-sources.md`](docs/data-sources.md) — endpoints, rate limits, licences, attribution

**Presentation**

- [`docs/benefits-and-impact.md`](docs/benefits-and-impact.md) — who this helps, and what is claimed
- [`docs/demo-script.md`](docs/demo-script.md) — the five-minute judge demo
- [`docs/ppt-deck.md`](docs/ppt-deck.md) — slide-by-slide deck content
- [`docs/architecture-diagram-brief.md`](docs/architecture-diagram-brief.md) — the architecture diagram prompt

## Contributing

Setup, conventions, and the traps worth knowing before you write code:
[`CONTRIBUTING.md`](CONTRIBUTING.md).

The backend suite runs entirely offline, so a clean clone can be fully verified with `make test`.

## Licence

[MIT](LICENSE) © 2026 Team Cogito Ergo Sum.

## Tooling

Backend: `uv` · FastAPI · SQLAlchemy 2 async · Alembic · NumPy · SciPy · OR-Tools · pydantic v2 ·
Ruff · pytest · Hypothesis.
Frontend: Next.js 16 · TypeScript · Tailwind v4 · ECharts · TanStack Query · zod.
