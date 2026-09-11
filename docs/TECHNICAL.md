# Technical Documentation — SIH26105

**AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform**

> **Tagline:** From CVE to ₹ impact to optimal security spend.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · NumPy / SciPy ·
OR-Tools CP-SAT · Next.js 16 · React 19 · TypeScript · Tailwind v4 · Apache ECharts

**Status:** Phases 0–8 complete · 244 backend tests passing · ruff + eslint + builds clean
**Companion deep-dives:** `TECHNICAL-EXPLAINED.md` (formulas + glossary) ·
`data-management-and-database.md` · `ml-and-ai.md` · `ui-and-ux.md` · `benchmark.md`

---

## 1. The one-paragraph summary

Existing security tools report **severity** (CVSS), not **financial risk**. A CVSS 10.0 on an
isolated test box looks identical to a CVSS 10.0 on the payment gateway, so they queue
identically. This platform closes that gap: it ingests real vulnerability intelligence, attaches
business context, models each risk as a **probability distribution** rather than a score,
computes financial exposure **in rupees**, and then solves — under a real budget — for the
portfolio that removes the most risk. Every number is traceable to its source and its
assumptions, and **no number originates in the language model**.

**There is no trained machine-learning model in this project** — see §11. That is deliberate.

---

## 2. Architecture

```text
① DATA INPUT          NVD CVE API 2.0 · CVSS v4→v3.1→v3.0→v2 · FIRST EPSS
                      CISA KEV · MITRE ATT&CK (19.2 → 697 techniques)
                      Organisation telemetry (CSV / Wazuh) · asset inventory
                                    ↓
② NORMALISATION       Canonical assets / findings / controls
                      CVE → ATT&CK → scenario linking
                      CVSS version-aware severity bands
                      Asset criticality (6 weighted dimensions)
                      Control effectiveness from evidence
                                    ↓
③ ANALYSIS ENGINE     FAIR factor model · LEF = TEF × Vulnerability
                      Beta-PERT three-point distributions
                      Monte Carlo (Poisson-thinning) · seeded RNG
                                    ↓
④ RISK OUTPUTS        EAL · P50 / P90 / P95 / P99 · VaR · CVaR
                      Loss-exceedance curve · provenance + confidence
                                    ↓
⑤ DECISION            Scenario engine (what-if) · CP-SAT budget optimizer
                      Overlap-aware, submodular risk reduction
                      Every portfolio RE-SIMULATED · baselines compared
                                    ↓
⑥ INTERFACES          REST API (FastAPI /api/v1) · Dashboard (Next.js + ECharts)
                      AI explanation layer (6 read-only tools)
                      Framework mapping: NIST · CIS · ISO · RBI · SEBI
```

**The governing rule:** numbers come from deterministic code; language is a view over those
numbers.

---

## 3. The FAIR risk model

Aligned to **Open Group Open FAIR** (O-RA 2.0.1 / O-RT 3.0.1), explicitly simplified — every
approximation is labelled in the UI, because an unlabelled simplification is a false claim.

```text
Risk = f(Loss Event Frequency, Loss Magnitude)

LEF = TEF × Vulnerability                      ← expected loss events per year
TEF = Contact Frequency × Probability of Action
Vulnerability = Pr(Threat Capability > Resistance Strength)   ← DERIVED
LM  = PLM + Bernoulli(SLEF) × SLM
```

| Term | Meaning |
|---|---|
| **Contact Frequency (CF)** | Threat-agent contacts per year (**attempts**, not successes) |
| **Probability of Action (PoA)** | Given contact, the chance the agent acts |
| **Threat Event Frequency (TEF)** | CF × PoA — threat events, **not yet** losses |
| **Threat Capability / Resistance Strength** | Attacker vs defender on a common percentile scale |
| **Vulnerability (V)** | `Pr(TC > RS)` — **derived, never an input** |
| **Loss Event Frequency (LEF)** | TEF × V — the bridge to money |
| **PLM / SLM** | Primary / secondary loss magnitude (amounts) |
| **SLEF** | Probability of a secondary loss (**a probability, not a rate**) |

**Three mistakes this structure prevents:**

1. **Putting PoA inside Vulnerability.** It belongs to TEF — a failed attack is a *threat event*,
   not a loss event. Conflating them inflates frequencies.
2. **Treating Vulnerability as a free input.** If you can type `V = 0.6`, the model will happily
   produce `LEF > TEF`, which is arithmetically impossible. Deriving V enforces
   `LEF ≤ TEF ≤ CF` by construction.
3. **Treating SLEF as a rate.** It is the probability that a secondary loss occurs at all.

### 3.1 Beta-PERT — three-point estimate → distribution

Analysts think in best case / most likely / worst case. SciPy has no `pert` distribution, so it
is built from a scaled Beta:

```text
μ   = (a + 4b + c) / 6                  mean (PERT convention, b weighted 4×)
α   = 1 + 4(b − a)/(c − a)              Beta shape parameters
β   = 1 + 4(c − b)/(c − a)
Var = (μ − a)(c − μ) / 7                PERT variance
sample: X = a + (c − a) · Beta(α, β)    shifted/scaled onto [a, c]
```

Chosen over triangular or normal because it honours the three estimates exactly, has a true mode
at `b`, is **bounded** (normal allows negative frequencies — nonsense), and is closed-form fast
enough to call 100,000 times per simulation.

### 3.2 Monte Carlo

For each of `N` trials: sample frequency factors → `LEF`; draw the event count from
**Poisson(LEF)**; for each event draw `PLM` and a **Bernoulli(SLEF)** coin-flip for secondary
loss; sum the year.

| Output | Meaning |
|---|---|
| **EAL** | Expected Annual Loss — the mean |
| **P50 / P90 / P95 / P99** | P95 = 5% of simulated years were worse |
| **VaR(p)** | Loss threshold at percentile p |
| **CVaR(p)** | *Average* loss given we exceeded that threshold — **coherent** where VaR is not |
| **Loss-exceedance** | `P(Loss > x) = 1 − CDF(x)` — the board-level tail view |

We report VaR **and** CVaR because VaR says where the cliff edge is but nothing about the drop,
and VaR is not subadditive. Defaults: 10,000 trials interactive, 100,000 for published tails —
tails converge far more slowly than the mean.

**Reproducibility:** `numpy.random.default_rng(seed)` (**PCG64**). Every simulation stores seed,
trial count, input hash, model version and library versions. Same inputs + same seed ⇒ identical
output. Without this no result is defensible.

---

## 4. Data management & database

### 4.1 Sources — three threat feeds, not one

| Source | What we take | Why it matters |
|---|---|---|
| **NVD CVE API 2.0** | CVSS base score + severity, CWE | Public, dated, authoritative **impact** |
| **FIRST EPSS** | Exploitation probability | **Likelihood**, which CVSS lacks |
| **CISA KEV** | Confirmed-exploited, ransomware flag | Ground truth that an exploit **exists** |
| **MITRE ATT&CK** | Enterprise techniques | Maps a finding to *how* it executes |
| **Org telemetry** | CSV / Wazuh, inventory | Makes it *this* organisation's risk |

CVSS alone is the classic error: a CVSS 10.0 nobody can reach outranks a CVSS 7.5 under active
exploitation. Modelling needs **frequency and magnitude**, and no single feed provides both.
Live enrichment: **18/18 findings** fully enriched with CVSS + EPSS + KEV.

### 4.2 Ingestion — adapters, not bespoke pipelines

```
ingestion/
├── base.py        HttpClient — shared retry / backoff / throttle / sleep hook
├── nvd.py         NVD CVE API 2.0
├── epss.py        FIRST EPSS daily scores
├── kev.py         CISA Known Exploited Vulnerabilities
├── mitre.py       MITRE ATT&CK enterprise STIX
├── csv_adapter.py org telemetry (CSV / Wazuh)
├── store.py       persistence + upsert
└── service.py     orchestration
```

`HttpClient` centralises what every feed would otherwise duplicate. `post_json` was added for the
LLM provider router, so the AI layer **inherited** the same retry/throttle policy rather than
rolling its own.

**Graceful degradation is explicit:** a source being down degrades *coverage*, not the run. If
NVD is unreachable we still model with the EPSS and KEV data we hold, and the evidence mix
visibly shifts toward lower-credibility sources.

### 4.3 Normalisation

`normalisation/taxonomy.py` (canonical categories, severity bands, asset classes) and
`vulnerabilities.py`. Two problems worth naming:

- **CVSS version drift.** NVD returns v2, v3.0, v3.1 and v4, and the same issue scores
  differently across them. We record the vector and version, use a **version-aware precedence
  chain (v4 → v3.1 → v3.0 → v2)**, and never compare across versions as one scale.
- **Identifier joining.** The same vulnerability arrives as a CVE (NVD), a probability (EPSS)
  and a boolean (KEV). Joined on `CVE-ID` into one internal record — which is what makes
  "CVSS 10.0 + EPSS 100% + in KEV" a single expressible fact.

### 4.4 Database schema — ten tables, three domains

**PostgreSQL** deployed, **SQLite** in tests (`aiosqlite`). SQLAlchemy 2.0 async with `asyncpg`.
A `json_type()` helper yields JSONB on Postgres and plain JSON elsewhere, so the same models work
in both — which is what lets the test suite run with zero infrastructure.

**① Organisational hierarchy** (`models/org.py`) — the context that turns a technical finding
into business impact:

```
Organization (id, name, sector, currency, framework_scope)
  └── BusinessUnit (criticality)
        └── Service (revenue_dependency, regulatory_scope)
              └── Asset (category, owner, internet_exposed, rto_hours,
                         criticality JSONB, criticality_score, criticality_band,
                         tags JSONB, provenance JSONB)
```

It mirrors how organisations assign ownership, and is what lets the **same CVE on two assets
resolve to two different rupee figures**.

**② Security** (`models/security.py`) — the observations:

```
Vulnerabilities   canonical CVE records (CVSS, EPSS, KEV, ATT&CK linkage)
Findings          vulnerability × asset — the join making it *our* problem
Controls          category, safeguards, cost, protects[]
ControlEvidence   coverage, configuration, policy, last-reviewed
```

The `Vulnerabilities` / `Findings` split matters: a CVE is a fact about the world, a finding is a
fact about *this estate*. Conflating them is what makes tools report identical risk for wildly
different exposures.

**③ Risk** (`models/risk.py`) — the results:

```
Scenarios    id, name, asset_id, service_id, category, status,
             cve_ids[], attack_techniques[], spec JSONB
Simulations  scenario_id, label, seed, n_trials, model_version, input_hash,
             eal, p50, p90, p95, p99, cvar_95, vulnerability, result JSONB
```

`Simulations` is the **reproducibility record**: seed + trials + input hash + model version means
any published figure can be re-derived and independently checked.

**Design decisions:** indexes on every FK plus `criticality_score`, `criticality_band`,
`input_hash` (the columns actually ranked and looked up); `CASCADE` down the org hierarchy but
`SET NULL` from scenarios to assets (a scenario survives its asset being retired, flagged
unassigned rather than vanishing); `TimestampMixin` on every table; JSONB where the shape is
genuinely variable.

> **Honest limitation:** the demo **serves from an in-memory planning context, not Postgres.**
> The schema is migrated and seeded, and Postgres backs ingestion and persistence — but it is
> **not on the read path for the demo API**. That is a deliberate trade for determinism, and it
> is the correct answer if asked whether the API is database-backed today.

---

## 5. Business context

### 5.1 Asset criticality

Weighted 1–5 across six dimensions, deliberately a **weighted sum, not a product**:

| Dimension | Weight | Question |
|---|---|---|
| Availability | 0.20 | How bad is downtime? |
| Integrity | 0.15 | How bad is corrupted data? |
| Confidentiality | 0.20 | How bad is disclosure? |
| Regulatory | 0.15 | What is the compliance exposure? |
| Internet exposure | 0.15 | How reachable is it? |
| Dependency centrality | 0.15 | How much breaks if it fails? |

Bands: `<2` LOW · `<3` MEDIUM · `<4` HIGH · `≥4` CRITICAL.

**Why not multiply:** a product means a single `1` anywhere zeroes the score — so the offline-only
backup server that is business-critical would score as worthless. A weighted sum lets dimensions
compensate, which matches how criticality behaves.

### 5.2 Control effectiveness — evidence, not a checkbox

```
base = 0.45·coverage + 0.30·configuration_strength + 0.25·policy_compliance
effectiveness = base × (1 − 0.25·recent_incident_signal) − staleness_penalty
```

"*We have MFA*" and "*we have MFA on the admin console, enforced, 98% enrolled, policy signed
last quarter*" are different risk postures. `recent_incident_signal` is a blunt, **visible** 25%
haircut — an incident the control should have prevented is evidence it underperforms its own
documentation, and a visible penalty beats a hidden fudge factor.

**Each control category moves a specific FAIR factor** — this is what makes the model causal
rather than correlational:

| Category | Mechanism | FAIR factor moved |
|---|---|---|
| **Avoidance** | fewer contacts | Contact Frequency ↓ |
| **Deterrent** | fewer agents act | Probability of Action ↓ |
| **Resistive** | harder to succeed | Resistance Strength ↑ → **Vulnerability recomputed** |
| **Responsive** | smaller losses | Loss Magnitude ↓ and/or SLEF ↓ |

So "enable MFA" does not apply a 15% discount to a score. It raises **Resistance Strength**,
which re-derives **Vulnerability** as `Pr(TC > RS)`, which lowers `LEF`, which propagates through
the *same* simulation. The effect is a **consequence** of the model, not an assertion about it.

---

## 6. Investment optimization (the technical differentiator)

```text
maximise   Σ rᵢ·xᵢ − Σ_{i<j} penalty(i,j)·z_ij      z_ij = x_i ∧ x_j
subject to Σ cᵢ·xᵢ ≤ B      budget
           x_a ⇒ x_b        prerequisites
           x_m = 1          mandatory controls
           xᵢ ∈ {0,1}

penalty(i,j) = min(rᵢ, rⱼ) · |Sᵢ ∩ Sⱼ| / max(|Sᵢ|, |Sⱼ|)
```

Risk reduction is **submodular**: `f(A∪{x}) − f(A) ≥ f(B∪{x}) − f(B)` for `A ⊆ B` — diminishing
returns, because controls overlap.

1. Adding up nominal reductions **overstates** the benefit.
2. Budget-constrained submodular maximization is **NP-hard**.

**Two-stage solution, and stage two is the honest part:**

1. **CP-SAT optimizes a *surrogate*** — standalone marginals minus pairwise-overlap penalties,
   linearized with auxiliary AND binaries. This only **proposes**; it never decides.
2. **Every portfolio — optimizer and all baselines — is scored by re-running the full Monte Carlo
   engine.** We report the **re-simulated** reduction, never the solver's own objective.

Most optimizers stop at stage 1 and report their surrogate score as if it were the real benefit.
Because the surrogate is conservative about overlap it can **under-select**, so a refinement pass
then improves the proposal against the true objective using **add** and **swap** moves — where
adding a control pulls in any unmet prerequisites as **one atomic move**, because a prerequisite
can be worthless alone yet gate something valuable (CSPM behind SIEM is exactly this shape).

**Baselines, all evaluated identically:** CVSS-first · EPSS-first · density-greedy (risk removed
per rupee) · cheapest-first · random · **brute-force exact optimum** (feasible at `n ≤ 12`).
Brute force exists to give a **bound** — without it, "the optimizer wins" is unfalsifiable.

### Benchmark result (`make benchmark`)

5 budgets (₹5L → ₹1 Cr) × 3 seeds × 20,000 trials, all via the same harness:

| Finding | Result |
|---|---|
| vs **CVSS-first** | Optimizer never loses — min gap **+0.00**, mean **+11.75 pp**, max **+28.25 pp** |
| vs **exact optimum** | Within **0.00 pp in all 15 runs** (optimal every time) |
| At ₹25L | ~44.9% risk removed vs 42.2% CVSS-first |

An earlier run — before the refinement pass — **lost to CVSS-first by 0.47 pp** at high budgets
where the whole candidate set was affordable. That is recorded here rather than quietly re-run,
because a benchmark that only reports wins is not a benchmark. (`docs/benchmark.md` is regenerated
by `make benchmark`, so it shows the fixed code; the finding is preserved in this document and in
`docs/research.md` §6.2.) It is also
precisely why portfolios are scored by re-simulation: **the re-simulation caught a defect the
solver's own objective hid.**

---

## 7. Framework compliance

**One internal ontology, many frameworks** — not a module per framework, which would duplicate
knowledge and drift apart. 38 canonical requirements each carry framework-native references, so
adding a framework is a **data change**.

| Framework | Type | Reference style | Requirements |
|---|---|---|---|
| NIST CSF 2.0 | standard | category (`PR.AA`) | 25 |
| CIS Controls v8.1 | standard | control number (`6.3`) | 21 |
| ISO/IEC 27001:2022 | standard | Annex A (`A.8.5`) | 25 |
| RBI IT Governance 2023 | regulation | thematic area | 24 |
| SEBI CSCRF | regulation | cybersecurity function | 25 |

**Coverage is computed, not declared:**

```
coverage(requirement) = 1 − Π (1 − effectiveness(controlᵢ))
```

The standard "probability at least one control holds" combination applied to measured
effectiveness. A requirement is not satisfied because a human ticked a box; it is satisfied **to
the degree its mapped controls actually work**.

**Gaps are priced** — each carries the rupee exposure of the scenarios it relates to plus the
candidates that would close it, so compliance competes for budget on the same footing as risk
instead of being a parallel exercise.

**CIS maps to fewer requirements than NIST — deliberately.** CIS v8.1 is an operational control
set, silent on governance, privacy and continuity. A **regression test asserts `CIS < NIST`** so a
future edit cannot silently turn the crosswalk into a copy. That test protects a modelling truth.

---

## 8. The AI layer

> **No number originates in the language model. Every figure is traceable to the engine.**

**Why be pedantic about the wording.** *"The LLM never computes a number"* is tempting and
technically **false**: if the engine returns `18,310,638` and the model writes "₹1.83 Cr", it has
divided and rounded. Three roles must be separated:

| Role | Who does it |
|---|---|
| **Originating** a quantity (EAL, P95, VaR, a portfolio's reduction) | the engine — never the LLM |
| **Converting / rounding** (₹1.83 Cr from 18,310,638) | the LLM — hence tolerance for unit scaling |
| **Selecting** which returned figures to cite | the LLM — a real risk: a true number against the wrong subject |

Row three is the caveat: **the grounding check verifies a figure is traceable, not that it was
attached to the correct subject.** State that before someone else finds it.

```
Question ──► RiskAgent (bounded loop, ≤ 4 steps) ──► tool selection
                                                       ↓
              6 read-only tools ──► ScenarioEngine ──► deterministic core
                                                       ↓
              results fed back ──► model renders prose
                                                       ↓
              GROUNDING CHECK: every figure matched against tool output
```

| Tool | Answers |
|---|---|
| `get_posture` | overall EAL / P90 / P95 |
| `get_top_risks` | ranked exposures with asset, CVSS/EPSS, weakest controls |
| `optimize_budget` | best portfolio for a budget + baseline comparison |
| `explain_control` | one control's effectiveness, FAIR factor, cost, upgrade path |
| `simulate_delay` | cost of postponing remediation N days |
| `get_framework_mapping` | coverage and priced gaps across seven frameworks |

Each returns **plain JSON** — deliberately not prose — so the same payload feeds the model *and*
is returned to the UI as **evidence** a user can audit.

**Read-only is enforced and tested:** no tool may mutate the engine. A tool that could write would
make answers order-dependent — the same question answered differently depending on what was asked
before it. A test asserts control effectiveness is unchanged after invoking every tool.

**Grounding check:** every numeric figure in the prose is extracted and matched against the
numbers the tools returned, tolerating rounding and unit scaling. Unmatched figures surface in
`grounding.unverified_numbers`. It is **heuristic and advisory** — it inspects final text, not
reasoning, and cannot prove correctness. Overclaiming here would be worse than having no check,
because it would manufacture false confidence.

**Provider fallback:** Groq → Gemini → OpenRouter (`:free`) → Ollama (local). All four expose an
**OpenAI-compatible** `/chat/completions`, so one code path serves them; only base URL, credential
and model differ. A provider without a credential is skipped.

**The deterministic fallback — the strongest single design decision.** With **no API keys at
all**, the platform still answers correctly: `route()` maps the question to a tool by pattern, the
engine computes, and `render()` composes the prose in Python. Same tools, same numbers, no network.

```
Q: What is our highest financial cyber risk?
→ route → get_top_risks() → engine computes → prose rendered in code
→ "Third-party service provider compromise on Public API gateway,
   ₹1.83 Cr expected annual loss (₹4.11 Cr at P95), CVSS 10.0"
```

This is not just an offline convenience. Because the no-LLM path produces **the same answers
through the same tools**, it *proves* the architectural claim: the intelligence lives in the
engine and the model is genuinely a language layer. A system whose answers break when you remove
the LLM has its intelligence in the wrong place.

---

## 9. Provenance and confidence

Every numeric parameter carries:

```
value · unit · source_type · source · source_date · confidence
assumption_description · model_version

source_type ∈ { PUBLIC_DATA, OBSERVED_TELEMETRY, USER_INPUT,
                MODEL_ESTIMATE, SYNTHETIC_DEMO }
```

Credibility is weighted per source rather than assumed equal:

| Source class | Credibility |
|---|---|
| PUBLIC_DATA (NVD, EPSS, KEV, ATT&CK) | 0.90 |
| OBSERVED_TELEMETRY | 0.85 |
| USER_INPUT | 0.60 |
| MODEL_ESTIMATE | 0.40 |
| SYNTHETIC_DEMO | 0.15 |

Banded **HIGH ≥ 0.75 · MEDIUM ≥ 0.50 · LOW**. On the demo estate the score is **0.254 — LOW**,
and it *should* be: 64% of inputs are synthetic. The dashboard displays this openly. A system
reporting HIGH confidence on a synthetic estate would discredit the one thing it claims.

**Demonstration estate:** 33 assets (16 CRITICAL / 11 HIGH / 6 MEDIUM), 8 services, 3 business
units, 11 controls, 24 findings, 8 scenarios. Enrichment: 18/18 findings with CVSS + EPSS + KEV;
ATT&CK enterprise 19.2 → 697 techniques.

**Headline example:** `CVE-2021-44228` appears on **3 assets at 3 different criticality bands** —
same CVE, three different rupee exposures and priorities. That is the story severity alone cannot
tell.

---

## 10. UI / UX

**One page, six panels, no navigation.** This was a deliberate reversal of an earlier
multi-screen design: a judge evaluating the system must hold the whole argument in mind at once —
exposure, causes, action, compliance, interrogation, trust. Splitting that across routes forces
them to remember what they saw two pages ago.

**Reading order is a decision funnel:**

| # | Panel | Question |
|---|---|---|
| 1 | Header + health badge | Is it live, and what is this? |
| 2 | **Posture strip** | How exposed are we, and how far should I trust it? |
| 3 | **Scenario explorer** | Where does that exposure come from? |
| 4 | **Investment optimizer** | What should we do about it? |
| 5 | **Framework alignment** | Does that satisfy our regulators? |
| 6 | **Ask the engine** | Can I interrogate it in my own words? |
| 7 | **Data confidence & assumptions** | Why should I believe any of this? |

The posture strip shows **four figures a CISO asks for first** — **Expected Annual Loss** (₹5.66 Cr),
**P90** (₹10.08 Cr, 1-in-10 year), **P95 / VaR** (₹11.75 Cr, 1-in-20 year) and the **Evidence
confidence band** (LOW · 25.4%) — plus the criticality mix and estate counts. Showing confidence
*next to* the headline number is the most important layout decision on the page: a rupee figure
without its confidence band invites false precision.

**Scenario explorer:** ranked list (exposure share bars) beside an inline detail pane — six
statistics (EAL, P90, P95, CVaR 95, Vulnerability, Loss Event Frequency), the loss-exceedance
curve and loss histogram annotated with P90/P95 markers, and candidate-control toggles that move
EAL live with a `before → after` banner. Below: **Cost of delay** and **Criticality stress test**.
A **Fast / Balanced / Precise** trial control (5k / 20k / 60k) is exposed on purpose — it teaches
that tail estimates tighten with samples, which is a real property of the model.

**Optimizer:** budget slider (₹5L → ₹1 Cr), one button, five statistics, the recommended portfolio
as chips showing each control's standalone reduction and the FAIR factor it moves, and a callout
comparing against CVSS-first. Then the evidence: a bar chart of every strategy's re-simulated
reduction beside a table of the same numbers — all scored on the **same harness**.

**Ask the engine:** question box with clickable suggestions; each answer shows **the tool calls
that produced it** (`get_top_risks()`, …) and whether it came from an LLM or the deterministic
path. Surfacing tool calls converts the AI from a black box into something auditable on screen.

**Data confidence & assumptions:** stacked bar of where every parameter came from, the assumptions
the result depends on, and the run fingerprint (`model v0.1.0 · 20,000 trials · seed 42`).

### UX engineering decisions

- **Every async surface has four states, not two:** loading (skeletons matching final geometry, so
  nothing jumps), **error with the reason and a Retry button**, deliberate empty state, success. A
  failed request must never look like a slow one — the previous version could spin forever on a
  dead API, the single worst failure mode in a live demo.
- **Accessibility built in:** `focus-visible` rings on all interactive elements, `aria-pressed` on
  toggles, `aria-current` on the active scenario, `role="alert"` on errors, `aria-live` on the Ask
  history, and colour never carries meaning alone (bands are labelled, not just coloured).
- **Truncation was a measured defect** — screenshot review found scenario titles cut mid-word.
  Fixed with two-line clamping and a scrollable list.
- **Sticky scenario list** on large screens; **jump-nav** anchor pills under the header.
- **Money in Indian short scale** (₹ Cr / ₹ L) via a shared formatter.
- **Server-side API proxy** (`src/app/api/[...path]/route.ts`) rather than exposing the API. This
  replaced a build-time `NEXT_PUBLIC_API_BASE_URL`, which was a genuine bug: `NEXT_PUBLIC_*` is
  inlined when the bundle is built, so a runtime value from Docker Compose was **silently ignored**
  and the app kept pointing at `localhost:8000`. A route handler reads the environment per
  request, so **one image works on localhost, behind a tunnel, or deployed** — and since the
  browser only talks to one origin, there is **no CORS surface**.
- **ECharts driven directly** (not `echarts-for-react`, which lags React 19 support).
- **TanStack Query** keyed on `[simulate, scenarioId, selectionKey, trials]` so re-simulation
  happens exactly when an input changes and not otherwise.

**Deliberately left out:** login/user management; separate routes per concern; live-editable
distribution parameters (they would break reproducibility — what-if changes *selection*, not the
underlying distributions); decorative animation.

---

## 11. ML position — what we do *not* do, and why

**There is no trained model.** Dependencies are `numpy`, `scipy`, `ortools` — no scikit-learn,
PyTorch, TensorFlow, XGBoost or LightGBM, and no artifact is trained or loaded anywhere.

| Layer | Technique | Is it ML? |
|---|---|---|
| Quantification | Monte Carlo + Beta-PERT | **No** — stochastic simulation |
| Decision | CP-SAT constraint optimization | **No** — combinatorial optimization |
| Explanation | LLM tool-calling agent | **Yes, but not ours** — a pre-trained third-party LLM |

**Why structural rather than statistical.** Supervised learning needs labelled outcomes of the
form *"this asset, this configuration, this threat → this actual rupee loss, this year."* That
data does not exist: organisations do not publish breach losses at asset granularity, losses are
**censored** (you observe only detected incidents), and the tail events that matter most have too
few examples to learn from — a once-in-twenty-years event has not happened twenty times.

Three failures an ML-first approach would produce here:

1. **No auditability.** A network saying "₹1.83 Cr" cannot show its work. A CFO cannot approve
   spend against an unexplainable number; an auditor cannot check it. Our FAIR decomposition can
   be challenged line by line.
2. **No extrapolation to rare events.** ML interpolates within its training distribution; cyber
   loss is heavy-tailed and the interesting questions live outside the observed range.
3. **Overfitting to a small demo estate.** Eight scenarios and 33 assets is not a training set.

FAIR is the standard answer to exactly this problem, which is why it is an Open Group standard
used in financial services. It encodes expert judgement as **explicit, challengeable parameters**
instead of hiding it in weights.

**The ML roadmap, with its precondition:** trend and anomaly detection over *accumulated
simulation history* — flagging distribution drift or quiet control decay. This is genuinely
ML-appropriate because it is **unsupervised** and needs no labelled outcomes, only time series.
It is **not built**: it requires history we do not yet persist (though `Simulations` already
stores `input_hash` and `model_version`, so the groundwork exists).

**How to say it:** *"We built a probabilistic risk model — FAIR against real NVD, EPSS and KEV
data — plus a constrained optimizer, and an LLM layer that explains results without producing
them."* Do **not** say "we built an ML model": there is nothing to point at when asked what was
trained.

---

## 12. API surface

All analytical endpoints under `/api/v1` (interactive docs at `/docs`).

| Method | Path | Purpose |
|---|---|---|
| GET | `/overview` | posture, counts, criticality mix, evidence confidence |
| GET | `/assets`, `/assets/{id}` | asset estate; detail adds findings + scenarios |
| GET | `/findings` | findings joined with NVD/EPSS/KEV intelligence |
| GET | `/controls` | control evidence, effectiveness, FAIR factor moved |
| GET | `/scenarios`, `/scenarios/{id}` | catalogue with ₹ exposure; detail has provenance |
| GET | `/candidates` | investment candidates (cost, prerequisites, impact) |
| POST | `/scenarios/{id}/simulate` | Monte Carlo for one scenario, optionally hardened |
| POST | `/portfolio/simulate` | re-simulate the estate with a selection applied |
| POST | `/optimize` | budget → portfolio + baseline comparison |
| POST | `/what-if/scenarios/{id}/{controls,delay,criticality}` | scenario analysis |
| GET | `/compliance`, `/compliance/frameworks`, `/compliance/requirements`, `/compliance/gaps` | framework alignment |
| POST | `/ask` | natural-language question → grounded answer |
| GET | `/ai/tools`, `/ai/status` | tool registry, provider chain |

Simulation responses return **binned histograms, percentiles and exceedance curves — never the
raw path array** — plus seed, trial count, model version and evidence mix. 100k raw samples per
scenario would swamp both the API and the browser.

---

## 13. Engineering practices

- **Deterministic core, AI at the edges** — all numbers from auditable code.
- **Reproducible by default** — seeded RNG; stored inputs and versions.
- **Honest uncertainty** — distributions with an evidence-mix label, not fake precision.
- **Adapters, not bespoke pipelines** — every source normalises to one schema.
- **Surrogate for search, simulation for claims** — never report the solver's own objective.
- **Tests fully offline** — mocked HTTP transports, committed fixtures, no real waits, so CI
  cannot flake on someone else's uptime; plus **at least one live end-to-end check per phase**,
  because mocks can agree with a bug.
- **Quality gates** — backend `ruff check` + `ruff format --check` + `pytest`; frontend `eslint`
  + `next build`.

---

## 14. Verification

| Phase | Area | State |
|---|---|---|
| 0 | Monorepo scaffold + Docker stack | ✅ |
| 1 | Scientific core — Beta-PERT, Monte Carlo, provenance | ✅ |
| 2 | Live evidence ingestion — NVD, EPSS, KEV, ATT&CK | ✅ |
| 3 | Business context + demo organization seed | ✅ |
| 4 | Investment optimizer — CP-SAT + baselines + harness | ✅ |
| 5 | Scenario engine + REST API | ✅ |
| 6 | Dashboard — single page, inline drill-down | ✅ |
| 7 | Compliance mapping — 7 frameworks, priced gaps | ✅ |
| 8 | AI layer — tool-calling + grounding check | ✅ |
| 9 | Deploy + proof | ⏳ |

**244 backend tests pass**; ruff and eslint clean; both builds clean. Dashboard verified rendering
in a real browser against the live API — posture, scenario drill-down with both charts, optimizer
portfolio, compliance coverage and the Ask panel all confirmed populated.

Each access gate is tested: unknown scenario/asset → 404, unknown candidate/criticality dimension
→ 422. Absence is never silently treated as zero.

Run it: `docker compose up --build` → web at `:3000`, API docs at `:8000/docs`.

---

## 15. Honest limitations

- **Absence from KEV ≠ safe.** It means *not yet confirmed exploited*, not *not exploitable*.
- **EPSS does not score every CVE.** A missing score is *unknown*, not zero — treating unknown as
  zero silently understates risk.
- **CVSS severity is not financial risk.** That is the entire premise of the project.
- **This is a risk-decision model, not an actuarial study.** Built to rank and allocate budget,
  not to reserve capital.
- **Control independence is assumed.** `1 − Π(1 − eᵢ)` assumes failures are independent; real
  controls share blind spots. A first-order approximation.
- **Submodular maximization is NP-hard**, so the CP-SAT portfolio is a strong candidate **scored
  on the true objective** — provably optimal only where brute force is tractable.
- **The AI grounding check is advisory and heuristic**, over final prose only. It verifies
  traceability, **not** correct attribution to a subject.
- **No ML model is trained** — see §11 for the data-precondition argument.
- **Trend/anomaly detection is not built**: it needs simulation history we do not persist.
- **The demo API reads a deterministic planning context, not Postgres.**
- **Demo financials are synthetic** and labelled `SYNTHETIC_DEMO` wherever they appear; the
  evidence confidence is legitimately **LOW**.

---

## 16. Glossary

**Risk / actuarial** — **FAIR** (Factor Analysis of Information Risk; Open Group taxonomy +
ontology, not a formula) · **LEF/TEF/CF/PoA** (each a strictly narrower subset of the one before)
· **PLM/SLM** (loss amounts) · **SLEF** (a *probability*) · **Threat Capability / Resistance
Strength** (attacker vs defender, compared to derive vulnerability) · **Beta-PERT** (three-point
estimate as a scaled Beta) · **heavy-tailed** (extreme outcomes far likelier than a normal curve)
· **Poisson process** (counting rare independent events per period) · **Bernoulli trial** (one
weighted coin flip) · **EAL** · **VaR** (threshold at a percentile; not subadditive) · **CVaR /
Expected Shortfall** (mean beyond the threshold; **coherent**) · **coherent** (combining
portfolios never looks riskier than the sum) · **loss-exceedance curve** · **convergence** (means
stabilise fast, tails slowly).

**Optimization** — **binary/integer program** · **NP-hard** · **submodularity** (diminishing
returns) · **marginal reduction** (gain given the current selection) · **surrogate objective**
(tractable stand-in used to *search*, never to *claim*) · **linearization** (expressing `x_i ∧ x_j`
as linear constraints with auxiliary binaries) · **CP-SAT** (OR-Tools constraint solver over
integer/boolean variables) · **prerequisite constraint** (`x_a ⇒ x_b`) · **brute-force
enumeration** (exponential, exact — hence our correctness bound) · **density greedy**.

**AI** — **tool / function calling** · **agent loop** (bounded to 4 steps here) · **grounding**
(anchoring language in retrieved fact) · **grounding check** (heuristic traceability test) ·
**hallucination** · **provider fallback / graceful degradation** · **OpenAI-compatible endpoint**
(the `/chat/completions` shape most providers implement) · **deterministic fallback** (same tools,
prose rendered in code).

**Engineering** — **provenance** (recorded origin of a value) · **PCG64** (modern NumPy bit
generator) · **binned histogram** (counts per bucket, returned instead of raw samples) ·
**adapter** (per-source translation to the canonical schema) · **censored data** (you observe only
detected events) · **structural vs statistical model** (explicit relationships vs fitted weights).
