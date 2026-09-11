# Architecture

## Positioning

The platform is not a security product and does not replace the security stack. It is a
**risk-decision layer** that sits above existing tooling and answers one question:
*given the current technical evidence and business context, where should the next rupee of
security spend go?*

```
SECURITY TELEMETRY                                   (Phase 2)
  vulnerability mgmt · SIEM · IAM · EDR · CSPM · asset inventory · threat intel
        │
        ▼
NORMALIZATION + ASSET CORRELATION                    (Phase 2/3)
        │
        ├── vulnerability facts (NVD/CVSS)
        ├── exploit signals (EPSS, KEV)
        ├── identity / control posture
        └── asset + business context
        │
        ▼
CYBER RISK SCENARIOS                                 (Phase 3)
        │
        ▼
PROBABILITY + LOSS DISTRIBUTIONS                     (Phase 1/5)
        │
        ▼
FINANCIAL RISK  (EAL / P90 / P95 / P99 / tail)
        │
   ┌────┴─────┐
   ▼          ▼
SCENARIO    BUDGET OPTIMIZER                         (Phase 5/4)
ENGINE          │
   └────┬───────┘
        ▼
SECURITY DECISIONS
        │
        ▼
EXECUTIVE + TECHNICAL VIEWS  +  FRAMEWORK MAPPING    (Phase 6/7)
```

## Components

| Layer | Module | Responsibility |
|---|---|---|
| Ingestion | `app/ingestion/` | One `TelemetryAdapter` interface; adapters for NVD, EPSS, KEV, MITRE ATT&CK, CSV, synthetic telemetry, Wazuh |
| Normalization | `app/normalization/` | Canonical `assets`, `findings`, `controls`; CVSS version fallback; CVE→ATT&CK→scenario linking |
| Risk | `app/risk/` | Beta-PERT distributions, FAIR frequency/magnitude, control effectiveness, Monte Carlo, provenance, metrics |
| Optimization | `app/optimization/` | Candidate controls, CP-SAT solver, baselines, portfolio evaluation harness |
| Compliance | `app/compliance/` | One normalized control catalog mapped to NIST CSF 2.0 / CIS v8.1 / ISO 27001 / RBI / SEBI CSCRF |
| AI | `app/ai/` | Provider router (Groq→Gemini→OpenRouter→Ollama), tool schemas, explanations, trend/anomaly |
| API | `app/api/` | FastAPI routers, Pydantic v2 schemas |
| Jobs | `app/jobs/` | Periodic ingestion entrypoint (cron) |
| Seed | `app/seed/` | Fictional demonstration organization (AICTE campus) |
| Web | `frontend/src/` | Next.js 16 + Tailwind v4 + ECharts dashboards |

## Data model (canonical)

```
Organization → BusinessUnit → Service → Asset
                                         ├── Vulnerability / Finding
                                         └── ControlEvidence
RiskScenario → FrequencyModel / MagnitudeModel / LossDistribution
InvestmentOption → Cost / ControlsAffected / Prerequisites / RiskReduction
FrameworkMapping
ModelParameter   (provenance on every numeric input)
Simulation       (reproducibility: seed, n, input hash, model version, lib versions)
```

## Provenance rule

Every numeric parameter stored or displayed carries:

```
value, unit, source_type, source, source_date, confidence,
assumption_description, model_version

source_type ∈ {PUBLIC_DATA, OBSERVED_TELEMETRY, USER_INPUT, MODEL_ESTIMATE, SYNTHETIC_DEMO}
```

Nothing synthetic is ever presented as measured fact. Any displayed figure can be traced
to its inputs, the seed, and the model version that produced it.

## Deployment topology

```
        ┌──────────────┐        ┌───────────────────────┐        ┌────────────────────┐
        │  Vercel       │  HTTPS │  Railway               │  TLS   │  Neon Postgres     │
        │  Next.js      │ ─────► │  FastAPI (always-on)   │ ─────► │  (pooled endpoint) │
        │  (Hobby, $0)  │        │  + cron ingest service │        │  (Free, 0.5 GB)    │
        └──────────────┘        └───────────────────────┘        └────────────────────┘
                                          │
                                          ▼
                        NVD 2.0 · EPSS · CISA KEV · MITRE ATT&CK
```

Local parity via `docker compose` (Postgres 16 + API + web).

## Design principles

1. **Deterministic core, AI at the edges.** All numbers come from auditable code; the LLM
   only queries and explains through tool calls.
2. **Reproducible by default.** Seeded simulations; stored inputs and versions.
3. **Honest uncertainty.** Outputs are distributions with an evidence-mix label, not
   single-point precision.
4. **Adapters, not bespoke pipelines.** Every telemetry source normalizes to one schema.
