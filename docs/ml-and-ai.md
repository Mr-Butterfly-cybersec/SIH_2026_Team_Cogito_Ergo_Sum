# ML & AI in SIH26105

> **Read this first.** There is **no trained machine-learning model in this project.** The
> dependencies are `numpy`, `scipy` and `ortools` — there is no scikit-learn, PyTorch,
> TensorFlow, XGBoost or LightGBM anywhere in the codebase, and no model artifact is produced,
> trained or loaded. If someone asks "what did you train and on what data?", there is no honest
> answer that starts with "we trained…".
>
> That is a deliberate engineering decision, explained in §2. The AI in this system is real and
> demonstrable — it is just **not** the kind of AI the phrase "ML model" implies. Knowing the
> difference, and being able to defend it, is worth more in a viva than an inflated claim that
> collapses under one question.

---

## 1. What is actually "intelligent" here

Three distinct things, and it is worth keeping them apart because they are often conflated:

| Layer | Technique | What it does | Is it ML? |
|---|---|---|---|
| **Quantification** | Monte Carlo simulation + Beta-PERT distributions | Turns uncertain estimates into a loss distribution | **No** — stochastic simulation |
| **Decision** | CP-SAT constraint optimization (OR-Tools) | Selects the budget-optimal control portfolio | **No** — combinatorial optimization |
| **Explanation** | LLM tool-calling agent (Groq/Gemini/OpenRouter/Ollama) | Selects a tool, renders the result as prose | **Yes, but not ours** — a pre-trained third-party LLM |

So: **the intelligence is in the model of the problem, not in a trained network.** The
economist's word for this is that we built a *structural* model — one where the relationships
are stated explicitly and the numbers are derived from them — rather than a *statistical* model
fitted to observations.

---

## 2. Why not machine learning? (the honest argument)

This is the strongest part of the story if you tell it properly, and the weakest if you bluff.

**You cannot train a supervised model without labelled outcomes, and nobody has them.**
A supervised cyber-risk model needs historical data of the form *"this asset, this
configuration, this threat landscape → this actual rupee loss, this year."* That data does not
exist: organisations do not publish breach loss figures at asset granularity, losses are
censored (you only observe the incidents that were detected), and the tail events that matter
most are precisely the ones with too few examples to learn from — by definition, a
once-in-twenty-years event has not happened twenty times.

Feeding a model on that data does not produce accuracy. It produces **confident-looking
numbers with no way to audit where they came from** — the opposite of what a financial risk
decision needs.

**Three concrete failures an ML-first approach would produce here:**

1. **No auditability.** A neural network that says "₹1.83 Cr" cannot show its work. A CFO
   cannot approve spend against a number whose derivation is unexplainable, and an auditor
   cannot check it. Our FAIR decomposition can be challenged line by line.
2. **No extrapolation to rare events.** ML interpolates within its training distribution. Cyber
   loss is heavy-tailed; the interesting questions live outside the observed range.
3. **Overfitting to a small demo estate.** Eight scenarios and 33 assets is not a training set.
   A model fit to it would memorise the demo, not learn risk.

**FAIR is the standard answer to exactly this problem**, which is why it is an Open Group
standard used in financial services rather than a research technique. It encodes expert
judgement as explicit, challengeable parameters instead of hiding it in weights.

**If you want an ML roadmap, state it as future work with its precondition:**

> Trend and anomaly detection over *accumulated simulation history* — flagging when a
> scenario's loss distribution drifts or a control's effectiveness quietly decays. This is
> genuinely ML-appropriate because it is *unsupervised* and needs no labelled outcomes, only
> time series. It is not built: it requires simulation history we do not yet persist.

That is the correct premise. It also happens to be true that we already store what it needs
(`Simulations` rows carry `input_hash` and `model_version`), so the groundwork is there.

---

## 3. What we DO claim, and how to defend each

### 3.1 Probabilistic risk quantification (not ML — and that's fine)

**Description:** a FAIR-based structural model where each risk is a distribution, not a score.

- **LEF = TEF × Vulnerability**, with **Vulnerability = Pr(Threat Capability > Resistance
  Strength)** — *derived*, never typed in. This is what guarantees `LEF ≤ TEF ≤ CF`, an
  invariant a scoring rubric cannot enforce.
- **Beta-PERT three-point estimates** turn an analyst's best/likely/worst into a bounded
  distribution (SciPy has no `pert`, so it is built from Beta).
- **Monte Carlo** samples frequency (Poisson) and magnitude, including a Bernoulli draw for
  secondary loss. 10,000 trials interactive, 100,000 for published tails.
- **Outputs:** EAL, P50/P90/P95/P99, **VaR** and **CVaR** (the coherent tail measure), plus the
  loss-exceedance curve.

**If asked "so where's the machine learning?"** — answer with §2. Structural over statistical,
because the labelled data required for supervised learning does not exist and would not be
auditable if it did.

### 3.2 Investment optimization (real optimization, not ML)

Budget-constrained portfolio selection with prerequisites and mandatory controls, solved as a
binary integer program.

Risk reduction is **submodular** — controls overlap, so funding two controls that protect the
same scenario yields less than the sum of their standalone gains, and naively adding up savings
**overstates** the benefit. Budget-constrained submodular maximization is **NP-hard**.

Our approach is two-stage and the second stage is the honest part:

1. **CP-SAT optimizes a surrogate** (standalone marginals minus pairwise-overlap penalties,
   linearized with AND variables). This only *proposes*.
2. **Every portfolio is re-scored by re-running the full Monte Carlo engine.** Optimizer and
   all baselines go through the identical harness. We report the **re-simulated** number, never
   the solver's own objective.

Then a refinement pass improves the proposal against the true objective, using **add** and
**swap** moves — where adding a control automatically pulls in any unmet prerequisites as one
atomic move, because a prerequisite can be worthless alone yet gate something valuable.

**Benchmark result (`make benchmark`, 5 budgets × 3 seeds, 20k trials):**
optimizer **never loses** to any baseline (min gap +0.00), and is within **0.00 percentage
points of the exact brute-force optimum in all 15 runs**. Median advantage over CVSS-first is
about **+12.7 points**.

### 3.3 The AI layer (this part genuinely uses an LLM)

**The division of labour — stated precisely:**

> **No number originates in the language model. Every figure is traceable to the engine.**

Worth being pedantic about, because the looser claim *"the LLM never computes a number"* is
technically false: if the engine returns `18,310,638` and the model writes "₹1.83 Cr", it has
divided and rounded. Three roles must be separated:

| Role | Who does it |
|---|---|
| **Originating** a quantity (EAL, P95, VaR, a portfolio's reduction) | the engine — never the LLM |
| **Converting / rounding** for readability (₹1.83 Cr from 18,310,638) | the LLM — which is why the grounding check tolerates unit scaling |
| **Selecting** which returned figures to cite | the LLM — a real risk: it could cite a true number against the wrong scenario |

Row three is the caveat. **The grounding check verifies a number is traceable, not that it was
attached to the right subject.** Say that before someone finds it.

**Six read-only tools**, each returning plain JSON (so the same payload feeds the model *and* is
shown in the UI as evidence):

| Tool | Answers |
|---|---|
| `get_posture` | overall EAL / P90 / P95 |
| `get_top_risks` | ranked exposures with asset, CVSS/EPSS, weakest controls |
| `optimize_budget` | best portfolio for a budget + baseline comparison |
| `explain_control` | one control's effectiveness, FAIR factor, cost, upgrade path |
| `simulate_delay` | cost of postponing remediation N days |
| `get_framework_mapping` | coverage and priced gaps across five frameworks |

**Bounds:** the agent loop is capped at 4 steps, and the tools cannot mutate state (enforced by
a test asserting the engine is unchanged after invoking every tool). Read-only means answers are
order-independent — the same question gives the same answer regardless of what was asked before.

**Grounding check:** every numeric figure in the generated prose is extracted and matched
against the numbers the tools actually returned, tolerating rounding and unit scaling.
Unmatched figures are surfaced in `grounding.unverified_numbers`. **It is heuristic and
advisory** — it inspects the final text, not the reasoning, and cannot prove correctness.

**Provider fallback:** Groq → Gemini → OpenRouter (`:free`) → Ollama (local). All four speak the
OpenAI-compatible `/chat/completions`, so one client serves them; a provider without a
credential is skipped. Ollama needs no key, so a fully local path always exists.

**The deterministic fallback — the strongest single design decision.** With **no API keys at
all**, the platform still answers correctly: `route()` maps the question to a tool by pattern,
the engine computes, and `render()` composes the prose in Python. Same tools, same numbers, no
network.

This is not just an offline convenience. Because the no-LLM path produces **the same answers
through the same tools**, it *proves* the architectural claim: the intelligence lives in the
engine and the model is genuinely a language layer. A system whose answers break when you remove
the LLM has its intelligence in the wrong place.

---

## 4. Verification

```
Q: What is our highest financial cyber risk?
→ route → get_top_risks() → engine computes → prose rendered in code
→ "Third-party service provider compromise on Public API gateway,
   ₹1.83 Cr expected annual loss (₹4.11 Cr at P95), CVSS 10.0"
   provider: deterministic · degraded: true · grounded: true
```

**244 backend tests pass**, including: tools are read-only; the optimizer never loses to a
baseline at any budget; refinement crosses a prerequisite valley; grounding accepts scaled
figures and flags invented ones; the agent terminates on a bad tool name and on step exhaustion.

---

## 5. How to talk about this

**Say:** *"We built a probabilistic risk model — FAIR against real NVD, EPSS and KEV data —
plus a constrained optimizer, and an LLM layer that explains results without producing them."*

**Don't say:** *"We built an ML model."* There is nothing to point at when someone asks what was
trained.

**If challenged on not using ML**, here is the whole answer in three sentences:

> Supervised learning needs labelled loss outcomes at asset granularity, and that data does not
> exist — breach losses are private, censored, and the tail events that matter most have too few
> examples to learn from. A model trained on it would give unauditable numbers to a decision
> that must be defensible line by line. So we used a structural FAIR model, where every
> parameter is explicit and challengeable, and where the uncertainty is reported rather than
> hidden — and we have an ML roadmap for unsupervised drift detection once we accumulate
> simulation history.
