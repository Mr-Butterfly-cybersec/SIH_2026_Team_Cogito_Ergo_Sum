# Benefits & Impact

Who this helps, what changes for them, and how we would know it worked. Written to be honest:
measured effects are separated from expected ones, and the limits are stated up front.

---

## 1. The one-line impact

An organisation stops asking *"which of these 240 vulnerabilities is worst?"* and starts asking
*"where does the next ₹25 lakh remove the most financial risk?"* — and can defend the answer.

---

## 2. The problem being solved (measured, not asserted)

Current practice ranks by **severity**. Three structural failures follow:

| Failure | Consequence |
|---|---|
| **CVSS has no likelihood** | A CVSS 10.0 nobody can reach outranks a CVSS 7.5 under active exploitation |
| **No business context** | The same CVE on the payment gateway and on a test box score identically |
| **No cost of the fix** | Severity ranking cannot weigh a ₹3L fix against a ₹90L one |

**Our benchmark quantifies the cost of that third failure** (`make benchmark`, 5 budgets × 3
seeds × 20,000 trials, all portfolios scored by re-simulation):

| Comparison | Result |
|---|---|
| Optimizer vs **CVSS-first** | Mean **+11.75 percentage points** more risk removed; it never lost a run |
| Best case | **+28.25 pp** (at ₹5L — where the budget is tightest and the choice matters most) |
| vs **exact optimum** | Within **0.00 pp in all 15 runs** — the answer is not merely better, it is right |
| At ₹25L | **44.9%** of modelled risk removed vs **42.2%** for CVSS-first |

That is the core impact claim, and it is reproducible: same seed, same trials, same numbers.

---

## 3. Benefits by stakeholder

### CISO / security leadership
- **A defensible number.** ₹5.66 Cr expected annual loss, ₹11.75 Cr at P95 — with a confidence
  band attached, not a score out of 100.
- **A budget conversation in business units.** "₹2.96 Cr of exposure sits behind our hardening
  gap" is a sentence a board understands; "CIS 4.1 non-compliant" is not.
- **Priority that survives challenge.** Each recommendation traces to a scenario, a control, a
  FAIR factor, and a re-simulated rupee figure.

### CFO / finance
- **Investment ranked by risk removed per rupee**, not by vendor enthusiasm.
- **Tail exposure made visible** — VaR and CVaR answer "how bad could a bad year be?", which a
  mean alone hides.
- **What-if before spending**: delay the fix 30 days and see the accruing loss; promote an asset
  to critical and watch exposure follow.

### Security engineering
- **Remediation order that is justified**, with prerequisites respected (a control gated behind
  another is funded as a chain, not skipped).
- **Evidence-based control effectiveness** — coverage, configuration strength, policy compliance
  and staleness, rather than a tick in a spreadsheet.

### Compliance / audit
- **One ontology, seven frameworks.** A single set of requirements that NIST, CIS, ISO 27001,
  ISO 42001, RBI, SEBI and the DPDP Act each name — so evidence is gathered once and reported
  seven ways.
- **Coverage computed from measured effectiveness**, not self-declaration.
- **Gaps priced in rupees**, so compliance competes for budget on equal footing.

### The organisation
- **Fewer unmanaged tail risks** — the risks that go unaddressed are the ones ranked by money,
  not by a technical score.
- **Faster, less contested budget cycles** because the ranking is auditable.

---

## 4. What makes this different from a scoring dashboard

Several commercial CRQ products exist, so "a dashboard with a rupee number" would not be a
contribution. The differentiators, each of which is testable:

| Claim | How a judge can verify it |
|---|---|
| **Deterministic and reproducible** | Same seed ⇒ identical numbers; seed and trial count stored on every result |
| **Real public evidence** | 18/18 findings enriched with live CVSS + EPSS + KEV; ATT&CK 19.2 (697 techniques) |
| **Optimizer beats the naive baseline** | `make benchmark` — and it reports where it *lost* before the fix, too |
| **Portfolios re-simulated, never summed** | Every strategy scored on the same harness; submodular overlap handled |
| **The LLM produces no numbers** | Remove the API key entirely — the same answers still come out of the engine |
| **Uncertainty is visible, not hidden** | Evidence mix shown; demo input confidence reads **LOW**, correctly |

The single most defensible one is the **deterministic fallback**. Because the platform answers
correctly with no LLM at all, the "AI" claim is *structurally* honest rather than rhetorical:
the intelligence is in the risk model, and language is a view over it.

---

## 5. Impact on decision quality — worked example

The demo estate, ₹25L budget, seed 42:

| | CVSS-first | Our optimizer |
|---|---|---|
| Controls funded | 6 | 6 |
| Spend | ₹24.5 L | ₹25.0 L |
| Risk removed | 42.2% | **44.9%** |
| ₹ risk removed per ₹ spent | 9.73 | **10.13** |

Same money, **+2.7 percentage points** of risk removed — because the optimizer funds what reduces
*modelled financial exposure*, while severity-first funds what scores highest. Scale that to a
₹1 Cr programme and the gap widens to the full measured range.

At a ₹5L budget the gap is **+28.25 pp** — which is the more important number. **Constraint bites
hardest when money is scarce, which is exactly when ranking method matters most.**

---

## 6. Broader impact

**Methodological.** Most security tooling treats quantification as a scoring exercise. This shows
an auditable alternative: a structural model where every parameter is explicit, every figure is
reproducible, and uncertainty is reported rather than suppressed.

**Regulatory (India).** RBI's 2023 IT Governance Direction and SEBI's CSCRF both push regulated
entities toward risk-based security budgeting. This gives them a way to answer "how was the
budget decided?" with a model rather than a narrative — and both frameworks are first-class in
the mapping layer, not bolt-ons.

**Educational.** The demonstration runs entirely on free public data with no paid API required,
and every input is labelled by origin. A team with no budget can reproduce the method.

**Honesty as a design property.** The evidence-confidence system makes "we don't know" a
first-class output. In a field where precise-sounding numbers are easy to manufacture, a system
that reports **LOW confidence on synthetic inputs** is a small contribution in itself.

---

## 7. What we do NOT claim

Being clear about this is what makes §3–5 credible.

- **Not an actuarial study.** Built to *rank and allocate*, not to reserve capital.
- **Demo financials are synthetic**, labelled `SYNTHETIC_DEMO`; headline confidence is **LOW**.
- **The demo API serves a deterministic planning context, not Postgres.**
- **No ML model is trained**, deliberately — labelled loss data at asset granularity does not
  exist, and a model fitted to 33 assets would memorise the demo.
- **The AI grounding check is heuristic** — it verifies a figure is traceable, not that it was
  attributed to the right subject.
- **No trend/anomaly detection yet** — it needs simulation history we do not persist.
- **Not a replacement for security tooling.** It sits *above* the stack as a decision layer; it
  consumes findings, it does not detect them.

---

## 8. How we would measure success in a real deployment

| Metric | How measured | Baseline | Target |
|---|---|---|---|
| Risk removed per rupee | Benchmark harness | CVSS-first | **≥ +10 pp** more risk removed |
| Decision reproducibility | Re-run with the stored seed | n/a | **100%** identical |
| Time to justify a budget line | Manual audit | hours | traceable in one screen |
| Evidence traceability | Provenance coverage | partial | **100%** of displayed figures |
| Synthetic-data disclosure | Audit of UI labels | n/a | **100%** labelled |
| Gap-to-optimum | Brute force where tractable | n/a | **0.00 pp** |

---

## 9. Verification

**303 tests pass**. Alongside the functional suite, property-based
fuzzing covers the engine and the HTTP surface — and it found four real defects that example
tests had missed:

1. **Metric overflow to `inf`.** A denormal baseline produced `-inf`, and `Infinity` is **invalid
   JSON** — one bad ratio would have corrupted an entire response.
2. **Incoherent CVaR < VaR.** Floating-point averaging could report a tail mean *below* the VaR
   threshold it is defined from.
3. **500 on `NaN` bodies.** FastAPI's own 422 handler crashed echoing the offending value back,
   so a malformed request returned a server error instead of a client error.
4. **Solver overflow.** A budget above ~9.2e16 exceeded CP-SAT's int64 coefficient range.

All four are fixed and covered by regression tests. Finding these is itself evidence for the
project's central argument: **claims should be tested against the inputs you did not think of.**
