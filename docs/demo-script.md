# Demo script (5 minutes)

## 0:00–0:30 — Establish the decision

Show the budget prompt:

```
Cybersecurity budget: ₹25,00,000
Question: Where should the next ₹25L go?
```

Then a conventional vulnerability dashboard (high / medium / low findings).

> "CVSS tells us severity. It does not tell us which investment removes the most business
> risk."

State that CVSS is one input, not the whole risk model.

## 0:30–1:30 — Evidence

Open one finding and show the chain:

```
CVE → CVSS → EPSS → KEV status → affected asset → asset criticality → control posture
       → business service → risk scenario
```

Real CVE identifiers, real scores, real exploitation signals.

## 1:30–2:30 — Financial risk

Show the Monte Carlo distribution:

```
EAL: ₹X   P50: ₹Y   P90: ₹Z
```

Open the assumptions drawer: evidence mix, source types, seed, model version. Say plainly
that the demo uses synthetic financial assumptions for a fictional organization, and that
the methodology is deterministic and inspectable.

## 2:30–3:30 — The killer scenario

Click **"Implement MFA for all privileged identities."** Coverage goes 0% → 100%; the
distribution shifts left.

```
EAL  before → after
P90  before → after
Risk reduction: XX%      Cost: ₹Y      ROSI-like: Zx
```

## 3:30–4:30 — Budget optimization

Run the optimizer with budget = ₹25L:

```
Recommended portfolio
 ✓ MFA
 ✓ Critical patch wave
 ✓ Network segmentation
 ✓ Backup hardening

Spend: ₹23.8L      Risk reduction: 42%
```

Then the comparison:

```
Naive highest-CVSS strategy   →  risk reduction 19%
Our optimizer                 →  risk reduction 42%
```

Both figures are re-simulated, not summed additively — overlapping controls are accounted
for.

## 4:30–5:00 — Board question

Ask the natural-language layer:

> "Why are we not spending the remaining budget on a larger SIEM deployment?"

It answers by citing the optimizer's actual result — the marginal annual-risk reduction
from SIEM expansion is lower than the remaining patch/MFA/segmentation options.

**End on the business decision**, which is what the problem statement asks for.

---

## Offline safety net

- Ask the same questions in a fixed order; keep 2–3 canned queries as fallback.
- Tool results are served from our database, not the model.
- The demo can run entirely locally if the network fails.
