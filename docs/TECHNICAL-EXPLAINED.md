# Technical Explainer — SIH26105

**Everything we built, why we built it that way, and what every unusual term means.**

This is the *deep* companion to `TECHNICAL.md` (the overview). Here every formula, every design
decision and every piece of jargon is spelled out — including the vocabulary from three fields
that do not normally sit in the same room: actuarial risk modelling, combinatorial
optimization, and applied LLMs.

**Reading order:** §1–2 are the mental model. §3–5 are the quantitative core. §6–8 are the
rest of the system. §9 is the detailed glossary — jump straight there if a word is unfamiliar.

---

## 1. The problem, stated precisely

Security tools output **severity**, not **risk**. A CVSS 10.0 on an isolated developer laptop
and a CVSS 10.0 on the payment gateway produce the same number, so they queue identically.

> **Severity** answers: *if this is exploited, how bad is it?*
> **Risk** answers: *how much money per year should we expect to lose to this?*

Risk needs **two** dimensions — how often, and how much. Severity collapses frequency to zero
and reports only impact. That is why severity-ranked queues systematically mis-allocate budget:
they cannot distinguish a catastrophic bug that is unreachable from a moderate bug that is
under active exploitation this week.

Our thesis: once risk is expressed in **rupees per year with an uncertainty range**, the
investment question becomes an optimization problem with a correct answer — and that answer
can be defended line by line.

---

## 2. The pipeline in one view

```
INGEST ──► NORMALISE ──► QUANTIFY ──► DECIDE ──► EXPLAIN
 NVD        canonical     FAIR +       CP-SAT     LLM calls
 EPSS       schemas       Monte Carlo  optimizer  tools, never
 KEV        CVE→ATT&CK    EAL, P95,    + re-sim   computes
 ATT&CK     criticality   VaR, CVaR    baselines
 telemetry  control eff.
```

The architectural rule that governs everything: **numbers come from deterministic code;
language is a view over those numbers.** The LLM is at the edge, never in the calculation.

---

## 3. The quantitative core

### 3.1 FAIR

**FAIR** = *Factor Analysis of Information Risk* (Open Group standard). It is a **taxonomy**
(what are the components of risk) plus an **ontology** (how they relate), not a formula you
plug numbers into. Our implementation follows O-RA 2.0.1 / O-RT 3.0.1, simplified — and every
simplification is labelled in the UI, because an unlabelled simplification is a false claim.

**The decomposition:**

```
Risk = f(Loss Event Frequency, Loss Magnitude)

LEF = TEF × Vulnerability                      ← expected loss events per year
TEF = Contact Frequency × Probability of Action
Vulnerability = Pr(Threat Capability > Resistance Strength)   ← DERIVED
LM  = PLM + Bernoulli(SLEF) × SLM
```

Reading each term:

| Term | Meaning | Why it is separate |
|---|---|---|
| **Contact Frequency (CF)** | How many times per year a threat *agent initiates contact*. | Attack attempts, not successes. |
| **Probability of Action (PoA)** | Given contact, the chance the agent actually acts. | Most scanning never escalates. |
| **Threat Event Frequency (TEF)** | CF × PoA — how many *threat events* per year. | Deliberately **not** yet a loss. |
| **Threat Capability (TC)** | How strong the attacker is, on a percentile scale. | Adversary-side. |
| **Resistance Strength (RS)** | How strong our defence is, same scale. | Defender-side. |
| **Vulnerability (V)** | `Pr(TC > RS)` — derived by comparing the two. | **Not an input.** |
| **Loss Event Frequency (LEF)** | TEF × V — how many events cause actual loss per year. | The bridge to money. |
| **Primary Loss Magnitude (PLM)** | Loss when the primary objective is hit. | Always occurs. |
| **Secondary Loss Event Frequency (SLEF)** | **Probability** that a secondary stakeholder reacts. | A probability, not a rate. |
| **Secondary Loss Magnitude (SLM)** | Cost of that reaction — fines, litigation, churn. | Occurs or not. |

**Three mistakes this structure prevents, and which most implementations make:**

1. **Putting Probability of Action inside Vulnerability.** It belongs to TEF, because a
   *failed attack is a threat event, not a loss event*. Confusing them inflates frequencies.
2. **Treating Vulnerability as a free input.** If you can type in `V = 0.6`, your model
   will happily produce `LEF > TEF` — arithmetically impossible. We *derive* V, so the
   ordering `LEF ≤ TEF ≤ CF` holds by construction.
3. **Treating SLEF as a rate.** It is the probability that a secondary loss occurs at all;
   treating it as a frequency double-counts.

This is why the model is *principled* rather than a weighted score: the relationships impose
constraints that a scoring rubric cannot.

### 3.2 Beta-PERT — turning three estimates into a distribution

Analysts think in three numbers: *best case, most likely, worst case*. That is a
**three-point estimate**. To simulate, we need a probability distribution.

**PERT** (Program Evaluation and Review Technique, from 1950s project management) defines the
mean of such an estimate as `(a + 4b + c) / 6` — the *most likely* value weighted 4×. But the
classic PERT gives only a mean, and SciPy has **no `pert` distribution**, so we construct the
equivalent as a scaled **Beta** distribution:

```
μ   = (a + 4b + c) / 6                      mean (PERT convention)
α   = 1 + 4(b − a)/(c − a)                  Beta shape parameters
β   = 1 + 4(c − b)/(c − a)
Var = (μ − a)(c − μ) / 7                    PERT variance, standard
sample: X = a + (c − a) · Beta(α, β)        shifted/scaled to [a, c]
```

Why we insist on Beta-PERT rather than a plain triangular or normal:

- It honours the analyst's three numbers exactly (support is `[a, c]` — no impossible samples).
- It has a proper **mode** at `b`, unlike a uniform.
- It is **bounded** — normal distributions allow negative frequencies, which is nonsense.
- Parameters are closed-form, so it is fast enough to call 100,000 times per simulation.

**Glossary tie-in:** *distribution* here means a mathematical description of which values are
likely, not a single number.

### 3.3 Monte Carlo simulation

**Monte Carlo** = instead of computing an answer analytically, sample the inputs randomly many
times and observe the distribution of outcomes. Named after the casino, because it is
literally repeated random draws.

For each of `N` trials we:

1. Sample the frequency factors → get `LEF`.
2. Draw the number of loss events from **Poisson(LEF)**.
3. For each event: sample `PLM`, and draw a **Bernoulli(SLEF)** coin-flip for the secondary loss.
4. Sum the year's losses.

**Poisson** is the standard distribution for *how many times a rare independent event occurs in
a fixed period* — exactly the shape of "loss events per year". **Bernoulli** is a single
weighted coin flip: secondary loss either happens for this event or it does not.

**Why simulate instead of using an average?** Because the answer is not an average. Losses are
**heavy-tailed** and **skewed**: the mean sits far above the median, and the events that matter
are in the extreme tail. A single expected value would hide precisely the scenario the business
needs to plan for. Simulation gives us the whole distribution — and the tail.

**What we report:**

| Output | Meaning |
|---|---|
| **EAL** — Expected Annual Loss | Mean annual loss. What to budget for on average. |
| **P50** | Median — half of simulated years were worse than this. |
| **P90 / P95 / P99** | Percentiles — "1 year in 20 was worse than this". |
| **VaR(p)** — Value at Risk | The loss threshold at percentile p. |
| **CVaR(p)** — Conditional Value at Risk | The **average** loss *given* we are past that threshold. |
| **Loss-exceedance curve** | `P(Loss > x) = 1 − CDF(x)` — the board-level view. |

**VaR vs CVaR** is worth internalising: VaR tells you *where the cliff edge is*; CVaR tells you
*how far the drop is*. VaR is silent about the severity beyond the threshold, and it is not
subadditive (two portfolios can each pass a VaR limit while their combination breaches it).
CVaR is **coherent** — it is subadditive — which is why we report both.

**Convergence and trial counts:** the mean stabilises quickly; the tail does not. We default to
10,000 trials for interactive use and 100,000 for published figures, because P99 from 10,000
samples is estimated from ~100 observations.

**Reproducibility.** We use `numpy.random.default_rng(seed)` — the **PCG64** generator, chosen
over the legacy `RandomState` for better statistical properties and a stable, documented
stream. Every simulation records the **seed**, **trial count**, an **input hash**, and the
**model + library versions**. Same inputs and same seed ⇒ byte-identical output. Without this,
no result is defensible — you could never show a judge the same number twice.

### 3.4 Asset criticality

Six weighted dimensions, each scored 1–5:

| Dimension | Weight | Question |
|---|---|---|
| Availability | 0.20 | How bad is downtime? |
| Integrity | 0.15 | How bad is corrupted data? |
| Confidentiality | 0.20 | How bad is disclosure? |
| Regulatory | 0.15 | What is the compliance exposure? |
| Internet exposure | 0.15 | How reachable is it? |
| Dependency centrality | 0.15 | How many things break if it fails? |

Bands: `<2` LOW · `<3` MEDIUM · `<4` HIGH · `≥4` CRITICAL.

**Deliberate design choice:** a **weighted sum**, not a **product**. Multiplying dimensions
means a single `1` anywhere zeroes the score — so the backup server that is offline-only but
business-critical would be scored as worthless. A weighted sum lets dimensions compensate,
which matches how criticality actually behaves.

### 3.5 Control effectiveness — evidence, not checkboxes

A control is **not** `true/false`. "We have MFA" and "we have MFA on the admin console, enforced,
with 98% enrolment and a policy signed last quarter" are different risk postures.

```
base = 0.45·coverage + 0.30·configuration_strength + 0.25·policy_compliance
effectiveness = base × (1 − 0.25·recent_incident_signal) − staleness_penalty
```

- **coverage** — what fraction of the estate is actually protected.
- **configuration_strength** — is it configured to spec, or deployed and forgotten?
- **policy_compliance** — is it mandated, owned and reviewed?
- **recent_incident_signal** — an incident that this control should have prevented is evidence
  the control underperforms its own documentation. A 25% haircut is deliberately blunt and
  visible rather than a hidden fudge factor.
- **staleness_penalty** — evidence that has aged is weaker evidence.

**Each control category moves a specific FAIR factor** — this is what makes the model causal
instead of correlational:

| Category | Mechanism | FAIR factor moved |
|---|---|---|
| **Avoidance** | fewer contacts happen | Contact Frequency ↓ |
| **Deterrent** | fewer agents act | Probability of Action ↓ |
| **Resistive** | harder to succeed | Resistance Strength ↑ → **Vulnerability recomputed** |
| **Responsive** | smaller losses | Loss Magnitude ↓ and/or SLEF ↓ |

So when we say "enable MFA", we are not applying a 15% discount to a risk score. We are moving
**Resistance Strength up**, which re-derives **Vulnerability** as `Pr(TC > RS)`, which lowers
`LEF`, which propagates through the *same* simulation. The effect is a consequence of the
model, not an assertion about it — and that is the difference between a quantified platform
and a dressed-up scoring spreadsheet.

---

## 4. Decision intelligence

### 4.1 The optimization problem

```text
maximise   Σ rᵢ·xᵢ − Σ_{i<j} penalty(i,j)·z_ij          z_ij = x_i ∧ x_j
subject to Σ cᵢ·xᵢ ≤ B                  budget
           x_a ⇒ x_b                    prerequisites
           x_m = 1                      mandatory controls
           xᵢ ∈ {0,1}, z_ij ∈ {0,1}     binary decisions

penalty(i,j) = min(rᵢ, rⱼ) · |Sᵢ ∩ Sⱼ| / max(|Sᵢ|, |Sⱼ|)
```

- `xᵢ = 1` means "fund control i". This is a **binary/integer program** — the class of
  optimization where decisions are yes/no.
- `rᵢ` is control i's **standalone** risk reduction.
- `Sᵢ` is the set of scenarios control i protects.
- The penalty term is the crux: two controls protecting the *same* scenarios overlap, so
  funding both gives less than the sum of their standalone gains.

### 4.2 Why this is genuinely hard (and what "submodular" means)

Risk reduction here is **submodular**: adding a control to a *large* selection helps less than
adding it to a *small* one. Formally, a set function `f` is submodular if
`f(A ∪ {x}) − f(A) ≥ f(B ∪ {x}) − f(B)` whenever `A ⊆ B` — **diminishing returns**.

Consequences that matter:

1. **Summing nominal reductions overstates the benefit.** If MFA and patching both claim to
   remove ₹50L, funding both does not remove ₹1 Cr.
2. Budget-constrained submodular maximization is **NP-hard** in general. You cannot expect an
   exact answer quickly, and you should distrust any tool that claims one cheaply.

**Glossary:** *NP-hard* means no known algorithm solves every instance in time polynomial in
the input size — so practical solvers find provably-good or empirically-good answers, and
problem size dictates the method.

### 4.3 How we solve it — and the honesty mechanism

We solve a **two-stage** process, and the second stage is what makes it defensible:

1. **CP-SAT optimizes a *surrogate*.** **CP-SAT** (Google OR-Tools) is a constraint-programming
   solver over integer variables — well suited to binaries with logical constraints
   (`x_a ⇒ x_b`) and capacities. The objective is the linearization above: standalone
   marginals minus pairwise-overlap penalties, with the product `x_i ∧ x_j` made linear via an
   auxiliary binary `z_ij`. This is an **approximation** of the true objective.
2. **Every portfolio is then scored by re-running the full Monte Carlo engine.** Optimizer and
   all baselines go through the *identical* evaluation. We report **re-simulated** reduction,
   never the surrogate.

> **Surrogate** = a mathematically convenient stand-in for the real objective. Useful for
> *searching*, never for *claiming*. Most optimizers stop at step 1 and report their surrogate
> score as if it were the real benefit. We do the opposite: the surrogate only chooses
> candidates; the engine decides who won.

**Baselines** (all evaluated identically, so the comparison is fair):

| Strategy | Logic |
|---|---|
| **CVSS-first** | highest severity first — what teams actually do |
| **EPSS-first** | most-likely-exploited first |
| **Density-greedy** | best risk-removed-per-rupee first |
| **Cheapest-first** | buy the most controls |
| **Random** | sanity floor |
| **Brute force** | exact optimum by enumeration, feasible at `n ≤ 12` |

Brute force exists to give us a **bound**: we can state how far the CP-SAT portfolio is from
the *best possible* answer, not merely that it beats the baselines. Without it, "the optimizer
wins" is unfalsifiable — it could still be leaving money on the table.

### 4.4 What-if analysis

Three parametric questions, each answered by re-simulation:

- **Control rollout** — apply a candidate (or set) and re-measure the estate.
- **Remediation delay** — postpone a fix `N` days; longer exposure ⇒ higher expected loss.
- **Criticality change** — promote/demote an asset; exposure follows the business signal.

These are **not** projections from a formula. Each one mutates the planning context and runs
the engine again, so the answer inherits every property of the core model.

---

## 5. Compliance mapping

**One internal ontology, many frameworks.** Five separate compliance modules would duplicate
knowledge and drift apart. Instead: **38 canonical requirements** in one internal vocabulary,
each carrying framework-native references.

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

This is the standard **"probability at least one control holds"** combination, applied to
effectiveness. The point: a requirement is *not* satisfied because a human ticked a box. It is
satisfied to the degree that the mapped controls actually work — as measured in §3.5.

Two consequences we are careful to state honestly:

- **Gaps are priced.** Each gap carries the rupee exposure of the scenarios it relates to, plus
  the investment candidates that would close it — so compliance competes for budget on the same
  footing as risk, instead of being a separate parallel exercise.
- **CIS maps to fewer requirements than NIST — deliberately.** CIS v8.1 is an operational
  control set; it is silent on governance, privacy and continuity. A **regression test**
  asserts `CIS < NIST`, so a well-meaning future edit cannot silently turn the crosswalk into
  a copy. That test exists to protect a modelling truth, not a formatting rule.

---

## 6. The AI layer

### 6.1 The rule

> **No number originates in the language model. Every figure is traceable to the
> deterministic engine.**

An LLM asked "what is our expected loss?" will produce a fluent, confident, *fabricated*
figure. In a financial risk product that is not a UX flaw, it is a correctness failure.

So the LLM is given no arithmetic role at all. It has **six read-only tools** (§6.2), it
selects one, the deterministic engine runs, and the model's only job is to turn the returned
JSON into prose.

**The precise claim, and why the looser one is wrong.** It is tempting to say "the LLM never
computes a number." That is *almost* true and technically false. If the engine returns
`18,310,638` and the model writes "₹1.83 Cr", it has divided and rounded — that is arithmetic.
Three distinct numeric roles must be kept apart:

| Role | Who does it | True? |
|---|---|---|
| **Originating** a quantity (EAL, P95, VaR, a portfolio's reduction) | deterministic engine | LLM never does this |
| **Converting / rounding / restating** (₹1.83 Cr from 18,310,638) | **the LLM does this** | this is why the grounding check tolerates unit scaling |
| **Selecting and ordering** which returned figures to mention | the LLM does this | a real risk: it could cite a true number against the wrong scenario |

The third row is the honest caveat. The grounding check verifies that a number is *traceable*
to tool output; it does not verify that the number was attached to the correct subject. A
figure can be present and misattributed, and the check will pass it.

**What makes the claim airtight:**

1. **In the demo as it ships, with no API keys, the answers are not LLM-generated at all.**
   `provider: deterministic` — `render()` composes the prose in Python, so for the demo the
   claim holds trivially.
2. **With a key configured, the model's context contains only tool output.** It has no channel
   to a rupee figure except through a tool, and no tools that mutate state.

**The formulation to use in a pitch:** *"Every number is produced by the deterministic engine
and traceable to its source. The model selects a tool and explains the result — it never
originates a figure."* That survives an informed challenge; "never computes a number" does not.

```
Question ──► RiskAgent (bounded loop, ≤ 4 steps) ──► tool selection
                                                       │
                        ┌──────────────────────────────┘
                        ▼
              6 read-only tools  ──►  ScenarioEngine  ──►  deterministic core
                        │
                        ▼
              tool results fed back ──► model renders prose
                        │
                        ▼
              GROUNDING CHECK: every figure matched against tool output
```

### 6.2 The tools

| Tool | Answers |
|---|---|
| `get_posture` | overall EAL / P90 / P95 |
| `get_top_risks` | ranked exposures with asset, CVSS/EPSS, weakest controls |
| `optimize_budget` | best portfolio for a budget + baseline comparison |
| `explain_control` | one control's effectiveness, FAIR factor, cost, upgrade path |
| `simulate_delay` | cost of postponing remediation N days |
| `get_framework_mapping` | coverage and priced gaps across the seven frameworks |

Each tool returns a **plain JSON dict** — deliberately not prose. The same payload feeds the
model *and* is returned to the UI as **evidence**, so a user can audit the answer.

"**Read-only**" is enforced and tested: no tool may mutate the engine. A tool that could write
would make answers order-dependent — the same question answered differently depending on what
was asked before it. A test asserts control effectiveness is unchanged after invoking every tool.

### 6.3 The grounding check

After the model produces prose, we **extract every numeric figure** from that text and verify
each one against the numbers the tools actually returned. This is a **grounding check** —
verification that generated language is *grounded* in retrieved fact rather than invented.

Tolerances are deliberate: rounding (`1.83` from `18310638`) and unit scaling
(`₹1.83 Cr ↔ 18,310,638`) are accepted, because those are correct transformations. Numbers
with no basis in tool output are surfaced in `grounding.unverified_numbers`.

**What it is not:** it is a heuristic over the *final prose*. It does not prove correctness, it
inspects text and not reasoning, and a figure can be present-but-misattributed. We label it
**advisory** everywhere and never claim it as a guarantee. Overclaiming here would be worse than
having no check at all, because it would manufacture false confidence.

### 6.4 Provider fallback

Groq → Gemini → OpenRouter (`:free`) → Ollama (local).

All four expose an **OpenAI-compatible** `/chat/completions` endpoint, so one code path serves
all of them; only the base URL, credential and model name differ. A provider with no configured
credential is skipped; the first success wins; if all fail, the request is served by the
**deterministic fallback**.

### 6.5 The deterministic fallback — and why it is the strongest part of the design

With no API keys at all, the platform still answers:

```
Q: What is our highest financial cyber risk?
→ route() matches intent → get_top_risks()
→ engine computes → render() writes the prose in code
→ "Third-party service provider compromise on Public API gateway,
   ₹1.83 Cr expected annual loss (₹4.11 Cr at P95), CVSS 10.0"
```

`route()` maps a question to a tool by pattern; `render()` composes the sentence with ordinary
string formatting. Same tools. Same numbers. No network.

This is not merely an offline safety net — it is the **proof of the architecture**. Because the
no-LLM path produces the *same answers* through the *same tools*, it demonstrates that the
intelligence lives in the engine and the model is genuinely only a language layer. A system
where removing the LLM breaks the answers has its intelligence in the wrong place.

Answers carry `degraded: true` and a reason, so the UI can never imply an LLM spoke when it
did not.

---

## 7. Provenance and confidence

Every numeric parameter carries:

```
value · unit · source_type · source · source_date · confidence
assumption_description · model_version

source_type ∈ { PUBLIC_DATA, OBSERVED_TELEMETRY, USER_INPUT,
                MODEL_ESTIMATE, SYNTHETIC_DEMO }
```

**Provenance** = the record of where a number came from and how it was derived. It is what makes
a figure **auditable**: a reviewer can trace it to a source and challenge the source.

Confidence is **credibility-weighted** (a public, dated, authoritative source outweighs a
model guess) and banded: **HIGH ≥ 0.75 · MEDIUM ≥ 0.50 · LOW** below.

The rule that keeps the demo honest: **synthetic inputs are labelled `SYNTHETIC_DEMO` and never
presented as measured fact.** A demo built on invented numbers is fine — as long as the
invention is visible.

---

## 8. Engineering practice

| Decision | Reason |
|---|---|
| **Deterministic core, AI at the edge** | Numbers must be reproducible and auditable. |
| **Seeded RNG everywhere** | A result you cannot reproduce is not evidence. |
| **Adapters, not bespoke pipelines** | Every source normalises to one schema; new feeds are additive. |
| **Binned outputs, never raw paths** | 100k raw samples per scenario would swamp the API and the browser; we return histograms, percentiles and curves. |
| **Tests fully offline** | Mocked HTTP transports, committed fixtures, no real network or waits — so CI is fast and cannot flake on someone else's uptime. |
| **One live end-to-end check per phase** | Mocks can agree with a bug; a real run catches it. |
| **Provenance on every parameter** | Enforced structurally, not by convention. |

**Quality gates:** backend `ruff check` + `ruff format --check` + `pytest` (303 tests);
frontend `eslint` + `next build`.

---

## 9. Glossary of novel and specialised terms

**Actuarial / risk**

- **FAIR** — Factor Analysis of Information Risk. Open Group standard framework decomposing
  risk into frequency × magnitude. A taxonomy plus ontology, not a formula.
- **LEF / TEF / CF / PoA** — Loss Event Frequency / Threat Event Frequency / Contact Frequency /
  Probability of Action. Each is a strictly narrower subset of the one before it.
- **PLM / SLM / SLEF** — Primary Loss Magnitude, Secondary Loss Magnitude, Secondary Loss Event
  Frequency. SLEF is a **probability**; PLM and SLM are **amounts**.
- **Threat Capability / Resistance Strength** — Attacker strength vs defender strength on a
  common percentile scale; comparing them **derives** Vulnerability.
- **Beta-PERT** — Three-point estimate (best/likely/worst) expressed as a scaled Beta
  distribution via the PERT mean `(a+4b+c)/6`.
- **Heavy-tailed / skewed** — Distributions where extreme outcomes are far more likely than a
  normal curve implies, and the mean sits above the median. Typical of cyber loss.
- **Poisson process** — Model for the count of rare, independent events in a fixed period;
  what we use to draw "number of loss events this year".
- **Bernoulli trial** — A single weighted coin flip; used for "did the secondary loss occur?".
- **EAL** — Expected Annual Loss: the mean of the simulated annual-loss distribution.
- **VaR (Value at Risk)** — The loss threshold at a given percentile. Silent about severity
  beyond the threshold; not subadditive.
- **CVaR / Expected Shortfall** — The *average* loss given we have exceeded the VaR threshold.
  **Coherent** (subadditive), which is why it is reported alongside VaR.
- **Percentile (P50/P90/P95/P99)** — P95 means 5% of simulated years were worse.
- **Loss-exceedance curve** — `P(Loss > x)`; the whole tail in one view.
- **Subadditive / coherent** — A risk measure is coherent if combining portfolios never looks
  riskier than the sum of their separate risks; VaR fails this, CVaR passes.
- **Monte Carlo simulation** — Estimating an outcome distribution by repeated random sampling.
- **Convergence** — How many samples before an estimate stabilises. Means converge fast; tails
  are slow, which is why P99 needs far more trials than EAL.

**Optimization / mathematics**

- **Binary / integer program** — Optimization over yes/no (or whole-number) decisions.
- **NP-hard** — No known algorithm solves every instance in polynomial time; exact solutions do
  not scale, so practical solvers approximate or bound.
- **Submodularity** — Diminishing returns: `f(A∪{x}) − f(A) ≥ f(B∪{x}) − f(B)` for `A ⊆ B`.
  The property that makes naive "add up the savings" wrong.
- **Marginal reduction** — The risk removed by a control *given the current selection*; shrinks
  as the selection grows.
- **Surrogate objective** — A tractable stand-in for the true objective, used to *search* but
  never to *claim*.
- **Linearization** — Reformulating a non-linear term (here `x_i ∧ x_j`) into linear constraints
  with auxiliary binaries, so a solver can handle it.
- **CP-SAT** — Google OR-Tools' constraint-programming solver over integer/boolean variables;
  strong on logical constraints and capacities.
- **Prerequisite constraint** — `x_a ⇒ x_b`: funding a requires funding b first.
- **Brute-force enumeration** — Trying every feasible combination; exponential, but gives the
  exact optimum for small `n`, hence our correctness bound.
- **Density greedy** — Picking the best benefit-per-cost option repeatedly; fast, not optimal.

**AI / LLM**

- **Tool calling / function calling** — The model emits a structured request to run a named
  function with arguments, instead of answering directly.
- **Agent loop** — Iterating model → tool → model until an answer or a step budget is hit.
  Ours is **bounded** (max 4 steps) to cap latency and cost.
- **Grounding** — Ensuring generated language is anchored in retrieved fact rather than
  model-internal guesswork.
- **Grounding check** — Our post-hoc verification that every figure in the prose matches a
  number a tool returned. Heuristic and advisory, not a proof.
- **Hallucination** — Fluent, confident, fabricated output. The specific failure this
  architecture exists to prevent in a financial context.
- **Provider fallback / graceful degradation** — Trying providers in order and degrading to a
  weaker-but-working path rather than failing outright.
- **OpenAI-compatible endpoint** — The `/chat/completions` request/response shape that most
  providers now implement, letting one client talk to all of them.
- **Deterministic fallback** — Our no-LLM answer path: same tools, prose rendered in code.

**Engineering**

- **Provenance** — The recorded origin and derivation of a value; what makes it auditable.
- **PERT-style three-point estimate** — Best/likely/worst, the natural analyst input format.
- **CP-SAT vs LP vs MIP** — Constraint programming vs linear programming vs mixed-integer
  programming; different solver families for different constraint shapes.
- **PCG64** — The modern NumPy bit generator; chosen for statistical quality and stable streams.
- **Binned histogram** — Counts per value bucket, returned instead of 100k raw samples.
- **Adapter** — A per-source module translating a foreign format into the canonical schema.

---

## 10. Limitations we state openly

- **Absence from KEV ≠ safe.** It means *not yet confirmed exploited*, not *not exploitable*.
- **EPSS does not score every CVE.** A missing score is *unknown*, not zero. Treating unknown
  as zero silently understates risk.
- **CVSS severity is not financial risk.** That is the entire premise of this project.
- **This is a risk-decision model, not an actuarial study.** It is built to *rank and allocate*,
  not to reserve capital.
- **Control independence is assumed.** Combining effectiveness as `1 − Π(1 − eᵢ)` assumes
  failures are independent; in reality controls share blind spots. First-order approximation.
- **The grounding check is heuristic**, over final prose only, and advisory.
- **Demo financials are synthetic** and labelled `SYNTHETIC_DEMO` wherever they appear.
- **Trend / anomaly detection is not built.** It requires simulation history we do not yet
  persist.
- **Submodular maximization is NP-hard**, so the CP-SAT portfolio is a strong candidate scored
  on the true objective — provably optimal only where brute force is tractable.
