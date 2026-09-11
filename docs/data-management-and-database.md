# Data Management & Database

How SIH26105 acquires, normalises, stores and traces its data — and why each choice was made.

---

## 1. Data sources

Everything numeric in the system traces to one of five source classes, recorded on every
parameter (see §6):

| Source | What we take | Why it matters |
|---|---|---|
| **NVD CVE API 2.0** | CVSS base score + severity, CWE, description | Public, dated, authoritative severity |
| **FIRST EPSS** | Exploitation probability (0–1) | Likelihood, not just impact |
| **CISA KEV** | Confirmed-exploited flag, ransomware association | Ground truth that an exploit exists in the wild |
| **MITRE ATT&CK** | Enterprise techniques (release 19.2 → **697 techniques**) | Maps a finding to *how* it would be executed |
| **Organisation telemetry** | CSV / Wazuh exports, asset inventory | Makes it *this* organisation's risk, not a generic score |

Live enrichment on the demo estate: **18 of 18 findings** fully enriched with CVSS + EPSS + KEV.

### Why three separate threat feeds and not just CVSS

They answer different questions, and no single one is sufficient:

- **CVSS** — *if* exploited, how bad? (impact only; says nothing about likelihood)
- **EPSS** — how likely is exploitation in the next 30 days? (probabilistic, but no impact)
- **KEV** — has it actually been exploited? (binary, but only covers confirmed cases)

CVSS alone is the classic mistake: a CVSS 10.0 that nobody can reach outranks a CVSS 7.5 under
active exploitation. Combining all three is what lets us model frequency *and* magnitude.

---

## 2. Ingestion architecture

The rule: **adapters, not bespoke pipelines.** Every feed is one module implementing a common
contract, so a new source is additive and never touches the rest of the system.

```
ingestion/
├── base.py        HttpClient — shared retry / backoff / rate-limit policy
├── nvd.py         NVD CVE API 2.0
├── epss.py        FIRST EPSS daily scores
├── kev.py         CISA Known Exploited Vulnerabilities
├── mitre.py       MITRE ATT&CK enterprise STIX
├── csv_adapter.py customer/org telemetry (CSV, Wazuh)
├── store.py       persistence + upsert
└── service.py     orchestration
```

**`HttpClient` (base.py)** centralises the concerns every feed would otherwise duplicate:
retries with backoff, request throttling, timeouts, and a shared `sleep` hook so tests can run
without real waiting. `post_json` was added alongside `get_json` when the LLM provider router
needed it — so the AI layer inherited the same retry and throttle policy instead of rolling
its own.

**Graceful degradation** is explicit: a source being down degrades *coverage*, it does not fail
the run. If NVD is unreachable we still model with the EPSS and KEV data we hold, and the
evidence mix (§6) visibly shifts toward lower-credibility sources. The system tells you what it
could not verify rather than silently omitting it.

---

## 3. Normalisation

Raw feeds never reach the risk engine. They pass through a canonical layer:

```
normalisation/
├── taxonomy.py         canonical categories, severity bands, asset classes
└── vulnerabilities.py  CVE → canonical vulnerability records
```

Two normalisation problems worth naming:

**CVSS version drift.** NVD returns scores under CVSS v2, v3.0, v3.1 and v4, and the same
underlying issue can score differently across versions. We record the vector and the version,
use a **version-aware precedence chain (v4 → v3.1 → v3.0 → v2)**, and never compare scores
from different versions as though they were the same scale.

**Identifier joining.** The same vulnerability appears as a CVE (NVD), a probability (EPSS)
and a boolean (KEV). Those are joined on `CVE-ID` into one internal record, which is what makes
"CVSS 10.0 + EPSS 100% + in KEV" expressible as a single fact about one finding.

---

## 4. Database design

**PostgreSQL** in deployment, **SQLite** in tests (via `aiosqlite`). SQLAlchemy 2.0 async with
`asyncpg`. JSONB on Postgres for flexible payloads, plain `JSON` elsewhere — expressed through
a `json_type()` helper so the same models work in both, which is what lets the test suite run
with zero infrastructure.

### Schema — ten tables in three domains

**Organisational hierarchy** (`models/org.py`) — the *context* that turns a technical finding
into business impact:

```
Organization (id, name, sector, currency, framework_scope)
  └── BusinessUnit (criticality, description)
        └── Service (revenue_dependency, regulatory_scope)
              └── Asset (category, owner, internet_exposed, rto_hours,
                         criticality JSONB, criticality_score, criticality_band,
                         tags JSONB, provenance JSONB)
```

The hierarchy is deliberate: it mirrors how a real organisation assigns ownership, and it is
what allows the same CVE on two assets to resolve to two different rupee figures.

**Security** (`models/security.py`) — the *observations*:

```
Vulnerabilities   canonical CVE records (CVSS, EPSS, KEV, ATT&CK linkage)
Findings          vulnerability × asset — the join that makes it *our* problem
Controls          category, safeguards, cost, protects[]
ControlEvidence   coverage, configuration, policy, last-reviewed — the inputs to effectiveness
```

Note the split between `Vulnerabilities` and `Findings`. A CVE is a fact about the world; a
finding is a fact about *this estate*. Conflating them is what makes tools report identical
risk for wildly different exposures.

**Risk** (`models/risk.py`) — the *results*:

```
Scenarios    id, name, asset_id, service_id, category, status, cve_ids[], attack_techniques[], spec JSONB
Simulations  scenario_id, label, seed, n_trials, model_version, input_hash,
             eal, p50, p90, p95, p99, cvar_95, vulnerability, result JSONB
```

`Simulations` is the reproducibility record: **seed + n_trials + input_hash + model_version**
means any published figure can be re-derived and independently checked. Without those four
columns a result is an assertion, not evidence.

### Design decisions

- **Indexes** on every foreign key, plus `criticality_score`, `criticality_band` and
  `input_hash` — the columns actually used for ranking and lookup.
- **Cascade rules are deliberate:** `CASCADE` down the org hierarchy (delete a service, its
  assets go), `SET NULL` for references to assets/services from scenarios (a scenario should
  survive its asset being retired, flagged as unassigned rather than vanishing).
- **`TimestampMixin`** on every table (`created_at`, `updated_at` with `onupdate`) — an
  audit trail without which "when did this change?" is unanswerable.
- **JSONB for evolving structures** (`spec`, `result`, `criticality`) where the shape is
  genuinely variable, with a migration path to columns once stable.

### Honest limitation

**The demo serves from an in-memory planning context, not from Postgres.** The schema above is
fully migrated and seeded, but `/api/v1/*` serves precomputed values so the demo is
deterministic and needs no database round-trip. Postgres backs the ingestion and persistence
paths; it is not on the read path for the demo. This is a deliberate trade for reproducibility
— and it is the honest answer if asked whether the API is database-backed today.

---

## 5. Seed data

`seed/org_demo.py` builds the fictional demonstration estate: **33 assets** (16 CRITICAL /
11 HIGH / 6 MEDIUM), 8 services, 3 business units, 11 controls, 24 findings, 8 scenarios.

Two things keep this defensible:

1. **It is deterministic** — a fixed snapshot, so every run produces identical numbers.
2. **It is labelled synthetic.** Injected values carry `source_type = SYNTHETIC_DEMO`
   throughout, which propagates into the confidence band rather than being averaged away.

A demo built on invented numbers is fine. Presenting invention as measurement is not — and the
provenance system exists specifically to make that distinction structural rather than a matter
of discipline.

---

## 6. Provenance — the data-integrity backbone

Every numeric parameter carries a provenance record:

```
value · unit · source_type · source · source_date · confidence
assumption_description · model_version
```

Credibility is weighted per source, not treated as equal:

| Source class | Credibility |
|---|---|
| `PUBLIC_DATA` (NVD, EPSS, KEV, ATT&CK) | 0.90 |
| `OBSERVED_TELEMETRY` (our own estate) | 0.85 |
| `USER_INPUT` (analyst estimate) | 0.60 |
| `MODEL_ESTIMATE` (inferred) | 0.40 |
| `SYNTHETIC_DEMO` (invented) | 0.15 |

The weighted mix becomes a **confidence score**, banded **HIGH ≥ 0.75 · MEDIUM ≥ 0.50 · LOW**.

On the demo estate that score is **0.254 — LOW**, and it *should* be: 64% of inputs are
synthetic. The dashboard displays this openly (the *Data confidence & assumptions* panel) rather
than burying it. A system that reported HIGH confidence on a synthetic estate would be lying
about the one thing it claims to be good at.

---

## 7. Summary

- **Three threat feeds, not one** — impact, likelihood and confirmed exploitation are
  different questions and CVSS alone conflates them.
- **Adapters with a shared HTTP policy** — new sources are additive; retry, throttle and
  degradation are handled once.
- **Canonical normalisation** — version-aware CVSS handling and CVE-ID joining.
- **Ten tables in three domains** — org hierarchy, observations, results.
- **Reproducibility as a schema feature** — seed, trial count, input hash and model version on
  every stored simulation.
- **Provenance on every parameter** — credibility-weighted, banded, and surfaced in the UI.
- **Stated limitation** — the demo API reads from a deterministic planning context, not
  Postgres; the persistence layer backs ingestion, not the demo read path.
