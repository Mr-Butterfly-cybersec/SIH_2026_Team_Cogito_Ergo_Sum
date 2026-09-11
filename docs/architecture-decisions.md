# Architecture decisions

Why the platform is built the way it is. Every entry records a decision, the reasoning behind it,
and what it costs — so a contributor can change something deliberately rather than accidentally.

Read `docs/architecture.md` for the component map, and `docs/methodology.md` for the formulas.
This document is about **judgement**, not structure.

---

## 1 · What this is

A **cyber-risk decision engine**. It converts security findings plus business context into an
uncertainty-aware financial loss distribution, then chooses the security investments that remove
the most modelled risk under a fixed budget — and explains why.

It is **not** a security dashboard. It sits above existing tooling as a risk-decision layer; it
consumes findings, it does not detect them.

> **Tagline:** from CVE to ₹ impact to optimal security spend.

**The problem it answers.** Existing tools report *severity* (CVSS), not *financial risk*. A CVSS
10.0 on an isolated test box looks identical to a CVSS 10.0 on the payment gateway, so they queue
identically. Once risk is expressed in rupees per year with an uncertainty range, allocating a
budget becomes an optimisation problem with a defensible answer.

---

## 2 · The decisions that shape everything

These five govern the rest of the codebase. If you are about to contradict one, that is allowed —
but do it knowingly.

### 2.1 Numbers come from deterministic code; language is a view over them

**Decision:** the language model never originates a number. It selects a tool, the engine
computes, and the model renders the result as prose.

**Why:** an LLM asked "what is our expected loss?" produces a fluent, confident, fabricated
figure. In a financial risk product that is a correctness failure, not a UX flaw.

**Precise form of the claim** — worth being exact, because the loose version is false. The model
*does* still round and convert units (₹1.83 Cr from `18,310,638`). So:

| Role | Who does it |
|---|---|
| **Originating** a quantity (EAL, P95, VaR) | the engine — never the model |
| **Converting / rounding** for readability | the model — hence the grounding check tolerates unit scaling |
| **Selecting** which returned figures to cite | the model — and it could cite a true number against the wrong subject |

**The caveat to state before someone finds it:** the grounding check verifies a figure is
*traceable* to tool output. It does **not** verify correct attribution to a subject. It is
heuristic and advisory, and is described that way everywhere.

**Proof it holds:** with **no API key configured at all**, the platform answers the same questions
with the same numbers, because both paths call the same tools and the fallback renders prose in
code. A system whose answers break when you remove the LLM has its intelligence in the wrong
place.

### 2.2 Every figure is reproducible from a stored seed

**Decision:** `numpy.random.default_rng(seed)` (PCG64). Every simulation records the seed, trial
count, an input hash, and the model and library versions.

**Why:** a result you cannot re-derive is an assertion, not evidence. A judge can re-run the same
calculation and get the same number.

**Cost:** trial counts must be chosen deliberately — 10,000 for interactive use, 100,000 for
published tail metrics, because tails converge far more slowly than the mean.

### 2.3 Uncertainty is a feature, not something to hide

**Decision:** every numeric parameter carries provenance; the mix of sources becomes a confidence
band shown next to the headline figure.

| Source class | Credibility |
|---|---|
| `PUBLIC_DATA` (NVD, EPSS, KEV, ATT&CK) | 0.90 |
| `OBSERVED_TELEMETRY` | 0.85 |
| `USER_INPUT` | 0.60 |
| `MODEL_ESTIMATE` | 0.40 |
| `SYNTHETIC_DEMO` | 0.15 |

Banded **HIGH ≥ 0.75 · MEDIUM ≥ 0.50 · LOW**.

**The demo estate reads LOW (0.254), and that is correct** — 64% of its inputs are synthetic. A
platform that reported HIGH confidence on a synthetic estate would discredit the one thing it
claims to do well.

### 2.4 Search on the surrogate; claim only from simulation

**Decision:** the optimiser searches with a cheap **surrogate** objective, then **every** candidate
portfolio — optimiser and all baselines — is scored by **re-running the full Monte Carlo engine**.

**Why:** risk reduction is **submodular** (controls overlap, so gains diminish), which makes naive
summation overstate the benefit, and budget-constrained submodular maximisation is **NP-hard**. The
surrogate is a mathematically convenient stand-in — useful for *searching*, never for *claiming*.

**What this caught:** the surrogate is conservative about overlap and therefore **under-selects**.
The first benchmark run *lost* to CVSS-first by 0.47 pp. Re-simulation exposed it; the solver's own
objective had hidden it.

**Where that finding lives now, stated precisely:** `docs/benchmark.md` is *regenerated* by
`make benchmark`, so it reflects the current code and no longer contains losing runs (the current
run shows 0 losses and 0.00 pp from the optimum). The record of the defect is **here and in
`docs/research.md` §6.2**, not in the generated file. The lesson is the point: a benchmark that only
reports wins is not a benchmark — and a generated artefact must not be mistaken for a historical
record.

### 2.5 A bound that can be violated is not a bound

**Decision:** brute-force enumeration supplies the exact optimum at small candidate counts, and the
benchmark **fails loudly** if the optimiser ever appears to beat it.

**Why:** nothing can beat an exhaustive search over all feasible portfolios. Appearing to means the
optimiser returned something *invalid* — most likely a portfolio with an unmet prerequisite.

This is not hypothetical. An earlier version of the check was **one-sided** (`gap <= 0.01`), so when
the optimiser "beat" the exact optimum by 4.88 points — the signature of an invalid answer — it
counted that as *optimal* and hid a real bug: the refinement swap move dropped `SIEM` while leaving
`CSPM` funded, whose prerequisite *is* SIEM. The optimiser was returning a portfolio you cannot buy.

**The general lesson, worth applying elsewhere:** verify against something that *could contradict*
you. A check that cannot fail is not a check.

---

## 3 · The risk model

### 3.1 FAIR, with Vulnerability derived

```
Risk  = f(Loss Event Frequency, Loss Magnitude)
LEF   = TEF × Vulnerability
TEF   = Contact Frequency (CF) × Probability of Action (PoA)
Vuln  = Pr(Threat Capability > Resistance Strength)     ← DERIVED, never an input
LM    = Primary Loss Magnitude + Bernoulli(SLEF) · Secondary Loss Magnitude
```

**Three distinctions the structure exists to enforce:**

1. **Probability of Action belongs to TEF, not Vulnerability.** A failed attack is a *threat event*,
   not a loss event. Conflating them inflates frequencies.
2. **Vulnerability is derived.** If it can be typed in, the model will happily produce `LEF > TEF`,
   which is arithmetically impossible. Deriving it enforces `LEF ≤ TEF ≤ CF` by construction.
3. **`SLEF` is a probability, not a rate.** A secondary loss can only follow a primary one.

### 3.2 Beta-PERT, because SciPy has no `pert`

```
μ = (a + 4b + c) / 6 · α = 1 + 4(b−a)/(c−a) · β = 1 + 4(c−b)/(c−a) · Var = (μ−a)(c−μ)/7
sample: X = a + (c − a) · Beta(α, β)
```

Chosen over triangular or normal because it honours three-point estimates exactly, has a true mode,
is **bounded** (a normal distribution permits negative frequencies — nonsense), and is closed-form
fast enough for 100,000 draws.

### 3.3 Asset criticality is a weighted sum, not a product

Six dimensions (availability .20, integrity .15, confidentiality .20, regulatory .15, internet
exposure .15, dependency centrality .15), bands `<2` LOW · `<3` MEDIUM · `<4` HIGH · `≥4` CRITICAL.

**Why not multiply:** a product means a single `1` anywhere zeroes the score — the offline-only
backup server that is business-critical would score as worthless. A weighted sum lets dimensions
compensate, which is how criticality actually behaves.

### 3.4 Controls are evidence, not checkboxes

```
base = 0.45·coverage + 0.30·configuration_strength + 0.25·policy_compliance
effectiveness = base × (1 − 0.25·recent_incident_signal) − staleness_penalty
```

Each control category moves a **specific FAIR factor**, and we shift that parameter and
re-simulate:

| Category | Mechanism | Factor moved |
|---|---|---|
| Avoidance | fewer contacts | Contact Frequency ↓ |
| Deterrent | fewer agents act | Probability of Action ↓ |
| Resistive | harder to succeed | Resistance Strength ↑ → **Vulnerability recomputed** |
| Responsive | smaller losses | Loss Magnitude ↓ and/or SLEF ↓ |

So "enable MFA" is not a 15% discount on a score. It raises Resistance Strength, which re-derives
Vulnerability, which lowers LEF, which propagates through the *same* simulation. The effect is a
**consequence** of the model rather than an assertion about it.

---

## 4 · Data

### 4.1 Three threat feeds, not one

| Feed | Question it answers | Blind spot |
|---|---|---|
| **NVD / CVSS** | if exploited, how bad? | no likelihood |
| **FIRST EPSS** | how likely in 30 days? | no impact |
| **CISA KEV** | has it actually been exploited? | only confirmed cases |
| **MITRE ATT&CK** | *how* would it execute? | — |

CVSS alone is the classic error: a CVSS 10.0 nobody can reach outranks a CVSS 7.5 under active
exploitation. Modelling needs frequency **and** magnitude, and no single feed provides both.

### 4.2 Adapters, not bespoke pipelines

Every feed is a module behind a shared `HttpClient` (retry, backoff, throttling, injectable
`sleep` so tests run without real waits). A new source is additive and never touches the rest.

**Graceful degradation is explicit:** a source being down degrades *coverage*, not the run. If NVD
is unreachable we still model with what we hold, and the evidence mix visibly shifts toward
lower-credibility sources.

### 4.3 The demo serves a planning context, not Postgres

The schema is migrated and seeded and Postgres backs ingestion — but `/api/v1/*` serves a
deterministic in-memory planning context so the demo needs no database round-trip and produces
identical numbers every time. **This is a deliberate trade for reproducibility**, and it is the
honest answer if asked whether the API is database-backed today.

---

## 5 · Compliance

**One internal ontology, many frameworks** — not a module per framework, which would duplicate
knowledge and drift apart. 25→**38 canonical requirements**, each carrying framework-native
references, mapped to **7 frameworks** (NIST CSF 2.0, CIS v8.1, ISO 27001, ISO 42001, RBI, SEBI,
DPDP).

Coverage is **computed** from measured control effectiveness, not declared:

```
coverage(requirement) = 1 − Π (1 − effectivenessᵢ)
```

Gaps are **priced in rupees**, so a compliance gap competes for budget on the same footing as any
other risk instead of being a parallel paper exercise.

**Two deliberate scoping decisions, each protected by a test:**

- **CIS v8.1 maps to fewer requirements than NIST** — it is an operational control set, silent on
  governance, privacy and continuity. A regression test asserts `CIS < NIST` so a future edit cannot
  silently turn the crosswalk into a copy.
- **ISO 42001 (AI) references no CIS control** — the cyber frameworks are entirely silent on AI
  management. Asserted, for the same reason.
- **DPDP has its own requirements** rather than aliasing ISO 27001, because notice, consent,
  data-principal rights and children's data have no Annex A equivalent.

---

## 6 · The AI layer

### 6.1 Six read-only tools

| Tool | Answers |
|---|---|
| `get_posture` | overall EAL / P90 / P95 |
| `get_top_risks` | ranked exposures with asset, CVSS/EPSS, weakest controls |
| `optimize_budget` | best portfolio for a budget + baseline comparison |
| `explain_control` | one control's effectiveness, FAIR factor, cost, upgrade path |
| `simulate_delay` | cost of postponing remediation N days |
| `get_framework_mapping` | coverage and priced gaps across seven frameworks |

Each returns **plain JSON**, not prose, so the same payload feeds the model *and* is returned to the
UI as auditable **evidence**.

**Read-only is enforced and tested:** a tool that could write would make answers order-dependent —
the same question answered differently depending on what was asked before it. A test asserts control
effectiveness is unchanged after invoking every tool.

### 6.2 The agent is bounded, and demands a tool call

The loop is capped at 4 steps, and **a first-step answer that cites no tool is rejected** rather
than shown. That guard exists because of a real failure: some local models do not support tool
calling, and `mistral:7b` replies *"let me call the tool named get_risk_posture"* as **prose**. No
structured call, no numbers — so the grounding check *passed* and a confident non-answer would have
been displayed while claiming an action it never took. Rejecting it falls back to the deterministic
path, which gives a genuine engine-backed answer.

### 6.3 Providers: configured is not the same as available

Chain: **Groq → Gemini → OpenRouter (`:free`) → Ollama (local)**. All four expose an
OpenAI-compatible `/chat/completions`, so one code path serves them; a provider without a credential
is skipped.

**`is_configured` (an offline fact) is deliberately separate from `probe()` (reachability plus model
presence).** A keyless provider is *always* configured, because its base URL is a non-empty string —
so treating configuration as availability made `/ai/status` report `active: ["ollama"]` on machines
with no Ollama running. The probe checks both that the server answers and that the configured model
is actually pulled, and returns a human-readable reason:

```
model 'llama3.2' is not pulled — `ollama pull llama3.2`
```

**Cost of this design:** `probe()` performs a network call, so its result is cached
(`PROBE_TTL_SECONDS`) because the dashboard polls the status endpoint.

**`chat()` deliberately does not gate on the probe** — the attempt *is* the reachability test, and a
cached probe can be stale.

---

## 7 · Frontend

### 7.1 One page, seven panels, no routing

A reversal of an earlier multi-screen design. A judge evaluating the system has to hold the whole
argument at once — exposure → causes → action → compliance → interrogation → trust — and routes
force them to remember what they saw two pages ago. Drill-down happens **inline**.

### 7.2 The runtime API proxy

`frontend/src/app/api/[...path]/route.ts` proxies to the API **per request**, reading
`API_PROXY_TARGET` from the environment at runtime.

**Why not a `rewrites()` rule in `next.config.ts`:** that file is evaluated at **build** time, so a
runtime env var is ignored and the destination is frozen. The same class of bug bit
`NEXT_PUBLIC_API_BASE_URL` — `NEXT_PUBLIC_*` is **inlined into the client bundle at build time**, so
setting it in `docker-compose.yml` did nothing and the app silently stayed pointed at
`localhost:8000`.

**Two consequences worth remembering:**

- One image works on localhost, behind a tunnel, or deployed — no rebuild.
- The browser only ever talks to one origin, so **there is no CORS surface at all**.

**Gotcha:** the catch-all route **strips `/api`** from `params.path`, so it must be put back when
building the upstream URL, or every request 404s.

### 7.3 Four async states, not two

Loading (skeletons matching final geometry, so nothing jumps), **error with the reason and a Retry
button**, deliberate empty, and success. A failed request must never look like a slow one — an
earlier version could spin forever on a dead API, which is the worst possible failure mode in a live
demo.

### 7.4 Motion is decorative, and yields

Rise/fade on mount, exposure bars growing from the left, a one-shot sweep when optimiser data lands,
a 1px hover lift. All of it collapses under `prefers-reduced-motion`, and **nothing that carries
information depends on an animation running**.

**Two implementation traps:**

- **`overflow: hidden` on a chart container clips ECharts tooltips** — they render as HTML inside the
  chart's div and legitimately extend past it. The sweep is therefore an animated *background
  gradient*, which is clipped by the element's own box and needs no overflow.
- **`window.resize` is not enough for charts.** They sit in a grid that reflows when the scenario
  list is toggled, so `Chart.tsx` uses a **`ResizeObserver`**.

**ECharts is driven directly**, not via `echarts-for-react`, which depends on APIs React 19 removed.

### 7.5 Accessibility is built in

`focus-visible` rings on every interactive element, `aria-pressed` / `aria-current` /
`role="alert"` / `aria-live`, hotkeys **1–6** to jump sections and **/** to focus the Ask input, and
colour never carries meaning alone — bands are labelled, not just coloured.

---

## 8 · Engineering conventions

- **Quality gates:** `ruff check` + `ruff format --check` + `pytest` for the backend; `eslint` +
  `next build` for the frontend. CI runs exactly these.
- **Tests are fully offline** — mocked HTTP transports, committed fixtures, no real waits. CI needs
  no secrets and cannot flake on someone else's uptime.
- **But at least one live end-to-end check per phase.** Mocks can agree with a bug.
- **Property-based tests (`test_fuzz.py`) exist because example tests only cover cases someone
  thought of.** They have found four real defects that the example suite missed — including a ratio
  returning `-inf` (invalid JSON, would corrupt a whole response) and a 500 where a 422 belonged.
- **Generate artifacts, don't hand-maintain them.** `docs/benchmark.md` is written by
  `make benchmark` and says so at the top. The distribution zip is built with `git archive` so it
  cannot drift from the committed tree.
- **A test that measures Monte Carlo noise is worse than no test.** Twice, a regression test failed
  from sampling error rather than a real defect. The fix both times: derive the tolerance from the
  standard error, or test against a **deterministic stub** instead of the simulator.

---

## 9 · Known limitations

Stated openly; the full list is in `docs/TECHNICAL.md` §15.

- **Absence from KEV ≠ safe.** It means *not yet confirmed exploited*.
- **A missing EPSS score is *unknown*, not zero.** Treating unknown as zero understates risk.
- **CVSS severity is not financial risk.** The entire premise of the project.
- **This is a risk-decision model, not an actuarial study** — built to rank and allocate, not to
  reserve capital.
- **Control independence is assumed** in `1 − Π(1 − eᵢ)`. Real controls share blind spots; this is a
  first-order approximation.
- **No ML model is trained**, deliberately. Supervised learning needs labelled loss outcomes at asset
  granularity, and that data does not exist; a model fitted to 33 assets would memorise the demo.
  Trend and anomaly detection is the ML-appropriate next step (unsupervised, needs only time series)
  and is **not built** — it requires simulation history we do not persist.
- **The demo API reads a planning context, not Postgres.**
- **Demo financials are synthetic**, labelled `SYNTHETIC_DEMO` wherever they appear.
