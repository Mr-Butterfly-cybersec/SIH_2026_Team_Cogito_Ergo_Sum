# Methodology

The quantitative core is a **FAIR-inspired, traceable model**. It follows the Open Group
Open FAIR taxonomy (O-RA 2.0.1 / O-RT 3.0.1) but is explicitly a simplified
operationalization — every place where we approximate is documented here and labelled in
the UI.

## 1. Factor decomposition (corrected)

```
Risk  = f(Loss Event Frequency, Loss Magnitude)

Loss Event Frequency (LEF) = Threat Event Frequency (TEF) × Vulnerability
Threat Event Frequency      = Contact Frequency (CF) × Probability of Action (PoA)
Vulnerability               = Pr(Loss Event | Threat Event) = Pr(Threat Capability > Resistance Strength)

Loss Magnitude (LM) = Primary Loss Magnitude (PLM) + Secondary Loss Magnitude (SLM)
Secondary Loss Event Frequency (SLEF) = Pr(Secondary Loss | Primary Loss)
```

Important distinctions:

- **Probability of Action is part of TEF, not Vulnerability.** A failed attack is a
  *threat event*, not a loss event.
- **Vulnerability is derived, never an input.** It falls out of comparing Threat
  Capability against Resistance Strength on a percentile scale.
- `LEF ≤ TEF ≤ CF` must always hold.
- `SLEF` is a **probability**, not a rate. A secondary loss can only occur after a primary
  loss.

## 2. Input data sources

| Factor | Modelled with | Typical source |
|---|---|---|
| Contact Frequency | Poisson (count process) | telemetry / estimate |
| Probability of Action | Beta-PERT on [0,1] | telemetry / estimate |
| Threat Capability | PERT on percentile scale 0–100 | threat intel, attacker profile |
| Resistance Strength | PERT on percentile scale 0–100 | control posture |
| Primary Loss components | PERT (or lognormal for heavy tails) | three-point estimates |
| Secondary Loss Event Freq. | Beta-PERT on [0,1] | three-point estimates |
| Secondary Loss components | PERT / lognormal | three-point estimates |

**CVSS is a severity signal, not risk.** EPSS is an exploitation-likelihood signal. KEV is
high-confidence evidence of in-the-wild exploitation. None of them is a complete risk
score; they enter as inputs alongside business context and control posture.

## 3. Beta-PERT (three-point → distribution)

For min `a`, most-likely `b`, max `c`, and classic PERT weight `λ = 4`:

```
μ   = (a + 4b + c) / 6
α   = 1 + 4(b − a) / (c − a)
β   = 1 + 4(c − b) / (c − a)
Var = (μ − a)(c − μ) / 7

sample:  X = a + (c − a) · Beta(α, β)
```

SciPy ships no `pert` distribution, so we build it from the Beta distribution.

## 4. Monte Carlo

For each of `N` trials:

1. Sample frequency-side factors → `TEF`, `Vulnerability` → `LEF`.
2. Draw the number of loss events from `Poisson(LEF)`.
3. For each event: draw `PLM`; draw `Bernoulli(SLEF)`; if it fires, draw `SLM` and add it.
4. Sum the annual loss.

Outputs:

- **EAL** = mean annual loss
- **P50 / P90 / P95 / P99** percentiles
- **Loss-exceedance curve**: `P(Loss > x) = 1 − CDF(x)`
- **VaR(p)** = p-th percentile; **CVaR(p)** = mean of losses at or above VaR(p)
- **Tornado** sensitivity across input alternatives

Defaults: `N = 10,000` for interactive use, `100,000` for published tail metrics. Tails
stabilise far more slowly than the mean, so tail figures always use the higher count.

**Reproducibility.** RNG is `numpy.random.default_rng(seed)` (PCG64). Every simulation
stores `seed`, `N`, an input-snapshot hash, the model version, and library versions. Same
inputs + same seed ⇒ same displayed result.

## 5. Control effectiveness

A control is an evidence object, not a boolean:

```
coverage, configuration_strength, recent_incident_signal,
policy_compliance, verification_age_days  →  bounded effectiveness ∈ [0,1]
```

Each control is mapped to the FAIR factor it actually moves:

| Control category | Effect | Factor moved |
|---|---|---|
| Avoidance | fewer contacts | Contact Frequency ↓ |
| Deterrent | fewer agents act | Probability of Action ↓ |
| Resistive | harder to succeed | Resistance Strength ↑ (Vulnerability recomputed) |
| Responsive | smaller losses | Loss Magnitude ↓ and/or SLEF ↓ |

Where possible we shift the *parameter* and re-simulate rather than applying a flat
percentage multiplier, because multiplying independent effectiveness values overstates
reduction when controls overlap.

## 6. Investment optimization

Objective: choose a portfolio of controls/remediations maximising modelled risk reduction
subject to a budget.

```
maximise   Σ rᵢ · xᵢ                          (rᵢ = risk removed by control i)
subject to Σ cᵢ · xᵢ ≤ B
           precedence: x_a ⇒ x_b              (prerequisites)
           mandatory:  x_m = 1
           xᵢ ∈ {0,1}
```

Risk reduction is **submodular** — controls overlap, so gains diminish. Two consequences:

1. Adding up nominal reductions overstates the true benefit.
2. The problem is a budget-constrained submodular maximization (NP-hard in general).

Implementation: OR-Tools **CP-SAT** with pairwise-overlap linearisation for the nominal
objective, then **every candidate portfolio is scored by re-running the Monte Carlo engine
with it applied**. Optimizer and baselines are therefore compared on *true* re-simulated
reduction, not on the surrogate. For small candidate sets (n ≤ 20) brute-force enumeration
provides the exact upper bound.

Baselines: **CVSS-first**, **EPSS-first**, **density-greedy (risk-reduction per rupee)**,
**cheapest-first**, and **random**.

## 7. Metrics

```
Risk reduction            = EAL_before − EAL_after
ROSI-like                 = (Risk reduction − annualized control cost) / annualized control cost
Risk removed per rupee    = Risk reduction / control cost
```

These are decision metrics, not accounting standards. We label them "ROSI-like" and define
the exact formula rather than implying actuarial precision.

## 8. Data confidence

Every financial output carries an **evidence mix** and a confidence level:

```
Evidence mix:  public vulnerability intel · observed telemetry · organization estimates · synthetic demo assumptions
Confidence:    HIGH / MEDIUM / LOW
```

This makes the uncertainty a visible feature rather than hiding it.

## 9. Caveats we state explicitly

- Absence from KEV is **not** evidence of zero exploitation risk.
- CVSS severity is **not** financial risk.
- This is a risk-decision model, **not** an actuarial study.
- Synthetic demonstration inputs are labelled as such wherever they appear.
- The LLM never produces or alters a number; it queries the engine and explains results.
