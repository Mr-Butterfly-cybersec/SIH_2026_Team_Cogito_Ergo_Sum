# Research

The research grounding for SIH26105: what the literature and standards prescribe, what the
commercial market already does, what we found empirically by building it, and what remains open.

**Companion documents:** `docs/sih26105-research-and-project-path.md` (the original feasibility
study, 2000 lines, with the full reference list) · `TECHNICAL.md` · `methodology.md` ·
`benchmark.md` · `ml-and-ai.md`

---

## 1. Research question

> **Can security investment be allocated by modelled financial risk — reproducibly, auditably,
> and without a trained model — such that the chosen portfolio demonstrably beats the ranking
> method practitioners actually use?**

That decomposes into four testable sub-questions, each answered in this document:

1. **Is severity ranking quantitatively worse?** (§6.1 — yes, by 11.75 pp on average)
2. **Can a constrained optimizer beat it, and is the answer provably good?** (§6.2 — yes, and
   provably optimal in all 15 benchmark runs)
3. **Can an LLM be used without it fabricating financial figures?** (§6.3 — yes, structurally)
4. **Can a structural model be honest about its own uncertainty?** (§6.4 — yes, and it must be)

---

## 2. What the standards prescribe

### 2.1 FAIR — the quantitative backbone

The Open Group's **Open FAIR** (O-RA 2.0.1 / O-RT 3.0.1) supplies the taxonomy and the
relationships. We adopt the factor decomposition and **derive Vulnerability** from
`Pr(Threat Capability > Resistance Strength)` rather than accepting it as an input — which is
what enforces the `LEF ≤ TEF ≤ CF` invariant that a scoring rubric cannot.

Three distinctions that the literature flags and most implementations get wrong (see
`methodology.md` §1):

1. **Probability of Action belongs to TEF, not Vulnerability.** A failed attack is a *threat
   event*, not a loss event.
2. **Vulnerability is derived, not typed in.** If it is an input, the model will happily produce
   `LEF > TEF`.
3. **SLEF is a probability, not a rate.**

### 2.2 Why CVSS cannot be the risk engine

FIRST is explicit that CVSS Base measures **severity**, not risk: Environmental and Threat
metric groups exist precisely because the same vulnerability scores differently in different
contexts. EPSS likewise warns that its probability is not a complete risk score.

Hence the three-feed model — each answers a different question, and none is sufficient alone:

| Feed | Question | Blind spot |
|---|---|---|
| **CVSS** | If exploited, how bad? | No likelihood |
| **EPSS** | How likely in 30 days? | No impact |
| **KEV** | Has it actually been exploited? | Only confirmed cases |

### 2.3 NIST — structure and governance

- **SP 800-30 Rev. 1** — risk assessment discipline (threat source, vulnerable condition,
  likelihood, impact, existing controls, residual risk, proposed treatment). Our scenario object
  mirrors this.
- **IR 8286 / 8286A / 8286B** — the cybersecurity risk register, estimation, and *prioritization
  incorporating projected cost of response*. This is the direct lineage of our optimizer.
- **SP 800-221** — aggregating ICT risk upward into the enterprise portfolio. Our
  `Asset → Service → BusinessUnit → Enterprise` hierarchy follows it.
- **IR 7385** — analytical, cost-effective, risk-based security budgeting. The closest prior
  work to the investment problem itself.
- **SP 800-55 Vol. 1** — measurement guidance that discusses VaR; **IR 8286C Rev. 1** discusses
  enterprise aggregation via PML/MFL and VaR-style reporting. This is why we report VaR and CVaR
  rather than inventing a metric.

### 2.4 NIST CSF 2.0 — the taxonomy, not the engine

Six functions (Govern, Identify, Protect, Detect, Respond, Recover), intentionally
outcome-oriented. We use it as a **reporting lens**, never as the risk model. NIST's Informative
References programme (and **SP 1347**) provides machine-readable crosswalks, including
ISO 27001:2022 → CSF 2.0 and CIS v8.1 → CSF 2.0 — the ecosystem that makes a single internal
ontology (§5) tractable.

### 2.5 Indian regulatory context

- **RBI Master Direction on IT Governance, Risk, Controls and Assurance Practices (Nov 2023)** —
  consolidated governance, risk assessment, VA/PT, incident response, access control, audit
  trails, change/patch management. It explicitly ties cybersecurity budget to the
  current/emerging threat landscape, which is a direct mandate for what we built.
- **SEBI CSCRF (Aug 2024)** plus clarification circulars (Dec 2024, Aug 2025) — six functions
  including Governance, with a graded approach by entity type/scale. Represented as **versioned**
  regulatory data.
- **CERT-In directions under §70B** — reporting and governance context; its audit guidance
  emphasises translating technical findings into business risk.
- **DPDP Act 2023 / Rules 2025** — a data-impact input where personal data is involved, *not*
  another compliance module.

### 2.6 Optimization theory

Budget-constrained **submodular maximization**. Risk reduction exhibits diminishing returns
(controls overlap), which makes naive summation systematically wrong and the problem NP-hard in
general. OR-Tools **CP-SAT** is the practical open-source solver for the constrained integer
formulation; brute force supplies the exact optimum at the candidate counts we model.

---

## 3. What the commercial market already does

CRQ is an established product category — SAFE, C-Risk/SAFE One, CyberHQ and others market FAIR
quantification, Monte Carlo, ROSI calculation and financial exposure. **Therefore a dashboard
with a rupee risk score is not a contribution.**

The differentiation is deliberate and narrow:

> **Open-data-driven, transparent, reproducible security-investment optimization with
> inspectable assumptions and a demonstrated optimizer-vs-baseline result.**

Vendor claims are treated as marketing, not evidence. Nothing here is evaluated against a
commercial product.

---

## 4. Method

### 4.1 Evidence model — hybrid, and labelled

**Live public intelligence** (NVD, EPSS, KEV, ATT&CK) + **synthetic organisational telemetry** +
**explicitly declared financial assumptions**. The rule is absolute: synthetic inputs are never
presented as measured fact, and the evidence mix propagates into a confidence band.

### 4.2 Why structural rather than statistical

This is the paper's answer to "where is the ML?".

Supervised learning requires labelled outcomes of the form *(asset, configuration, threat) →
actual rupee loss this year*. That data does not exist publicly at asset granularity, is
**censored** (only detected incidents are observed), and — decisively — the tail events that
dominate expected loss are, by definition, too rare to learn from. A model fit to such data
produces confident output with no audit trail, which is the opposite of what a capital-allocation
decision requires.

FAIR is the field's answer to this exact problem, which is why it is an Open Group standard used
in financial services: it encodes expert judgement as **explicit, challengeable parameters**.

### 4.3 Reproducibility as a methodological requirement

Every simulation stores `seed`, `n_trials`, `input_hash`, `model_version` and library versions.
A result that cannot be independently re-derived is an assertion, not evidence.

---

## 5. Design decisions traceable to research

| Decision | Grounded in |
|---|---|
| FAIR factor decomposition, derived Vulnerability | Open FAIR O-RA 2.0.1 / O-RT 3.0.1 |
| CVSS as severity signal, not risk | FIRST CVSS v4 guidance |
| EPSS/KEV as separate likelihood and exploitation inputs | FIRST EPSS; CISA KEV |
| Outcome-oriented control taxonomy | NIST CSF 2.0 |
| Scenario object shape | NIST SP 800-30 Rev. 1 |
| Risk register as canonical object; prioritization by cost of response | NISTIR 8286 / 8286A / 8286B |
| Asset → Service → BusinessUnit → Enterprise aggregation | NIST SP 800-221 |
| Cost-effective risk-based budgeting as the core problem | NISTIR 7385 |
| VaR / CVaR reported rather than an invented metric | NIST SP 800-55 Vol. 1; IR 8286C Rev. 1 |
| **One internal ontology, many frameworks** | CSF 2.0 Informative References; SP 1347 |
| RBI and SEBI as regulation overlays, versioned | RBI 2023 Direction; SEBI CSCRF + clarifications |
| CP-SAT for the constrained integer program | OR-Tools documentation |
| Submodular-aware evaluation (re-simulate, never sum) | submodular maximization literature |
| Provenance on every parameter | the stated requirement that synthetic ≠ measured |

Two decisions are **deliberate departures** worth naming as findings rather than omissions:

- **Weighted-sum criticality, not a product of dimensions.** Multiplying six 1–5 factors produces
  absurd nonlinearity and lets a single `0` erase an otherwise critical asset — the offline-only
  backup server that is business-critical would score as worthless.
- **`1 − Π(1 − eᵢ)` for combined control coverage** is a first-order independence assumption. We
  adopt it *and label it*, rather than presenting it as exact.

---

## 6. Empirical findings

Everything in this section is reproducible: `make benchmark` (5 budgets × 3 seeds × 20,000 trials)
and `uv run pytest tests/test_fuzz.py`.

### 6.1 Severity ranking is quantitatively worse — and it is worst when money is tight

| Comparison | Result |
|---|---|
| Optimizer vs CVSS-first, mean | **+11.75 pp** more risk removed |
| Best case (₹5 L budget) | **+28.25 pp** |
| At ₹25 L | 44.9% vs 42.2% |
| vs exact optimum | within **0.00 pp in all 15 runs** |

The most interesting result is where the gap is **largest**: at the tightest budget. Constraint
bites hardest when resources are scarce, so the *ranking method* matters most precisely where it
is usually least examined.

### 6.2 The surrogate is not the objective — and the benchmark nearly hid a defect

The first benchmark run **lost to CVSS-first by 0.47 pp** at budgets where the whole candidate set
was affordable. The cause was substantive: CP-SAT optimizes a *surrogate* (standalone marginals
minus pairwise-overlap penalties), which is conservative about overlap and therefore
**under-selects** — it declined to fund the next control even though re-simulation showed it was
worth funding.

**Two methodological lessons, both retained in the repository rather than edited away:**

1. **Search on the surrogate; claim only from simulation.** Had we reported the solver's own
   objective, the defect would have been invisible.
2. **A benchmark that only reports wins is not a benchmark.** Note that `docs/benchmark.md` is
   *generated* — the current run reflects the fixed code (0 losses, 0.00 pp from the optimum), so
   the record of the defect lives in this document, not in the generated artefact.

The fix was a refinement pass against the *true* re-simulated objective (**add** and **swap**
moves), where adding a control pulls in unmet prerequisites as **one atomic move** — because a
prerequisite can be worthless alone yet gate something valuable (CSPM behind SIEM is exactly this
shape, and greedy acceptance can never cross that valley).

A follow-on methodological finding: the first regression test for this failed on **Monte Carlo
noise at 2,000 trials**, not on search logic. It was rewritten against a **deterministic stub
landscape** — a test that measures noise is worse than no test.

### 6.3 Fabrication is a structural problem, not a prompting problem

An LLM asked for expected loss will produce a fluent, confident, invented figure. Prompting alone
does not fix this. The finding is that **architecture does**: give the model no arithmetic role,
expose only read-only tools, and verify its prose against the numbers the tools returned.

The decisive evidence is the **deterministic fallback**. With no API key configured, the platform
answers the same questions with the same numbers, because both paths call the same tools and the
fallback renders prose in code. This converts a claim into a demonstration: *the intelligence is in
the engine*.

Corollary finding, and one we state rather than hide: the **grounding check verifies traceability,
not correct attribution**. A model can cite a real number against the wrong scenario and pass. It
is heuristic and advisory, and is described that way everywhere.

### 6.4 Property-based testing found defects that example tests had missed

Hypothesis-driven fuzzing over the engine and the HTTP surface found **four real defects** — each
invisible to the example suite because each required an input nobody thinks to type:

| Defect | Why it mattered |
|---|---|
| **Metric overflow to `inf`** | A denormal baseline (`3e-302`) produced `-inf`; `Infinity` is **invalid JSON**, so one bad ratio corrupts an entire response body |
| **CVaR < VaR** | Floating-point averaging could place the tail mean *below* the VaR threshold it is defined from — a mathematically incoherent pair |
| **500 on `NaN` bodies** | FastAPI's own 422 handler crashed **echoing the offending value back**; a client error surfaced as a server error |
| **Solver int64 overflow** | A budget above ~9.2e16 exceeded CP-SAT's coefficient range |

A further finding was **about the tests, not the code**: two fuzz assertions failed for
harness reasons, and diagnosing them produced two reusable lessons —

- **Tolerance must come from the standard error, not from the mean.** A Beta(1,5) has ~85%
  relative spread, so `2% of mean` was half a standard error — a test that would fail randomly.
- **Fuzz inputs must be reachable.** A raw control character cannot appear in a URL; httpx rejects
  it before the request is sent. Testing it tests the client, not the server.

### 6.5 Honesty about uncertainty is enforceable, not aspirational

Credibility-weighting the evidence mix yields **LOW (0.254)** confidence on the demo estate, and
that is the *correct* output: 64% of inputs are synthetic. Making "we don't know" a first-class
result — rather than averaging it into a confident-looking number — is a finding we would defend
as a contribution in a field where precise-sounding figures are cheap to manufacture.

---

## 7. Consolidation: what is verified

| Claim | Evidence | Status |
|---|---|---|
| Optimizer beats CVSS-first | `benchmark.md`, 15 runs | ✅ mean +11.75 pp, 0 losses |
| Optimizer is optimal at this scale | brute-force comparison | ✅ 0.00 pp gap, all runs |
| Results are reproducible | seeded RNG + stored inputs | ✅ 100% |
| Real public evidence used | 18/18 findings enriched | ✅ CVSS + EPSS + KEV |
| LLM produces no numbers | deterministic fallback path | ✅ verified with no keys |
| Inputs are honestly labelled | provenance + evidence mix | ✅ LOW confidence surfaced |
| Engine is numerically robust | 44 property-based tests | ✅ 303 tests total |
| **No ML model is trained** | dependency audit | ✅ stated, not hidden |

---

## 8. Open problems

Stated as open, not as done:

1. **Trend and anomaly detection.** Requires simulation history we do not persist. This is
   genuinely ML-appropriate (unsupervised, time-series — no labelled outcomes needed), and
   `Simulations` already stores `input_hash` and `model_version`, so the groundwork exists.
2. **Calibrating synthetic loss magnitudes** against an authoritative Indian source. Currently
   labelled `SYNTHETIC_DEMO`; the methodology does not depend on the specific values.
3. **Relaxing the control-independence assumption** in `1 − Π(1 − eᵢ)`. Real controls share blind
   spots; a correlation structure would be more faithful.
4. **Scaling the optimizer** beyond the candidate counts where brute force is tractable — the
   gap-to-optimum bound is only available at `n ≤ 12`.
5. **Attribution-aware grounding.** Current verification confirms a figure exists in tool output,
   not that it is attached to the right subject.
6. **Live connector validation** against real Wazuh/SIEM deployments rather than replay adapters.

---

## 9. Contribution summary

1. A working, reproducible **FAIR-based quantification engine** on live public intelligence.
2. A **two-stage optimizer** that searches on a surrogate and *claims* only from re-simulation —
   with the surrogate's failure mode documented rather than concealed.
3. A **tool-calling AI layer** whose no-LLM fallback proves the numbers originate in the engine.
4. A **single-ontology framework crosswalk** with gaps priced in rupees, where a regression test
   protects the crosswalk from degenerating into five copies of one framework.
5. **Provenance and evidence-confidence** as enforced system properties rather than documentation.
6. A **property-based test suite** that found four defects example tests could not, and two
   lessons about writing honest tests.

---

## 10. References

The full annotated reference list (problem statement, NIST publications, Open FAIR, FIRST CVSS
and EPSS, CISA KEV, MITRE ATT&CK, CIS Controls, RBI, SEBI, CERT-In, DPDP, OR-Tools, Wazuh, and
commercial CRQ vendors, with URLs) is in **`sih26105-research-and-project-path.md` §36**.
Source endpoints, rate limits, licences and required attributions are in **`docs/data-sources.md`**.
