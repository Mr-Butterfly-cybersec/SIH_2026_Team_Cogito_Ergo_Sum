# SIH 2025 — Project PPT Layout

> Maximum: 6 slides including the title slide.
> Keep content concise. Prefer points, diagrams, infographics, and pictures over paragraphs.

---

## Slide 1 — Title

### Problem Statement
- **Problem Statement ID:** SIH26105
- **Problem Statement Title:** AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform
- **Theme:** Blockchain & Cybersecurity
- **PS Category:** Software
- **Team ID:** `[TEAM ID]`
- **Team Name:** `[TEAM NAME]`

**Visual:** dark, bold title slide. Tagline under the title:
> **"From CVE to ₹ impact to optimal security spend."**

---

## Slide 2 — Idea / Proposed Solution

### Problem → Solution

**What is the current problem?**
- Security tools report **severity** (CVSS), not **financial risk**.
- A CVSS 10.0 on an isolated test box looks identical to a CVSS 10.0 on the payment gateway.
- ₹1 crore budgets are allocated by "highest CVSS" or the loudest vendor — not by risk removed.

**Who faces the problem?**
- CISOs / security leads who must justify budget to management.
- Colleges and SMEs with no dedicated cyber-risk-quantification (CRQ) team.
- Auditors who need traceable, defensible justification for spend.

**Why are existing approaches insufficient?**
| Approach | Answers | Misses |
|---|---|---|
| CVSS / scanners | How severe is the flaw? | Business context, exploit reality, money |
| EPSS / KEV | Exploitation likelihood | Impact — not a full risk score |
| Risk registers (spreadsheets) | Qualitative RAG ratings | No uncertainty, no optimization |
| GRC dashboards | Compliance posture | Not a spend decision |

**Our proposed solution (one line):**
> A transparent **cyber-risk decision engine** that converts security findings + business
> context into an uncertainty-aware **financial loss distribution**, then selects the best
> investments under a fixed budget and **explains why**.

### Core Features
1. **Continuous ingestion & normalization** — NVD/CVSS, EPSS, CISA KEV, MITRE ATT&CK + org telemetry.
2. **Business-context risk scoring** — asset criticality + service dependency, not severity alone.
3. **Monte Carlo quantification** — EAL, P50/P90/P95/P99, VaR/CVaR in ₹ with visible uncertainty.
4. **Budget-constrained optimizer** — CP-SAT portfolio selection with re-simulated risk reduction.
5. **AI explain + what-if** — natural-language Q&A and scenarios (e.g. MFA rollout), numbers from the engine only.

### Innovation & Uniqueness
- **Money, not scores** — outputs are rupee loss distributions, not severity ratings.
- **Submodular-aware optimization** — controls overlap, so every portfolio is **re-simulated**, never summed additively.
- **Provenance on every number** — value · source type · date · confidence; nothing synthetic shown as measured.
- **No number originates in the LLM** — the AI selects a tool, the deterministic engine computes, and the model explains. Every figure traces back to the engine.
- **Beats the naive baseline** — measured against highest-CVSS first on the same harness.
- **Zero-cost stack** — runs on free tiers, usable by a college or an SME.

**Visual:** `Problem → Proposed Solution → Key Features` (3-column flow).

---

## Slide 3 — Technical Approach

### System Architecture

```text
          ┌──────────────────────────────────────────────┐
          │ Data / Input                                 │
          │ NVD·CVSS · EPSS · CISA KEV · MITRE ATT&CK    │
          │ org telemetry (CSV / Wazuh) · asset inventory│
          └──────────────┬───────────────────────────────┘
                         ↓
          ┌──────────────────────────────────────────────┐
          │ Pre-processing / Normalization               │
          │ canonical assets · findings · controls       │
          │ CVE→ATT&CK linking · asset criticality       │
          └──────────────┬───────────────────────────────┘
                         ↓
          ┌──────────────────────────────────────────────┐
          │ Detection / Analysis Engine                  │
          │ FAIR factor model → Monte Carlo              │
          │ LEF = TEF × Vulnerability                    │
          │ EAL · P50/P90/P95/P99 · VaR / CVaR           │
          └──────────────┬───────────────────────────────┘
                         ↓
          ┌──────────────────────────────────────────────┐
          │ Decision / Intelligence                      │
          │ CP-SAT budget optimizer + baselines          │
          │ scenario engine · AI explain (tool-calling)  │
          └──────────────┬───────────────────────────────┘
                         ↓
          ┌──────────────────────────────────────────────┐
          │ Dashboard / Output                           │
          │ executive + technical views · ₹ exposure      │
          │ framework mapping (NIST/CIS/ISO/RBI/SEBI/DPDP)│
          └──────────────────────────────────────────────┘
```

### Technology Stack
- **Backend:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Alembic
- **Analytics:** NumPy · SciPy · OR-Tools CP-SAT
- **Frontend:** Next.js 16 · TypeScript · Tailwind v4 · Apache ECharts
- **AI layer:** Groq tool-calling → Gemini → OpenRouter `:free` → Ollama (local fallback)
- **Deployment:** Vercel (web) · Railway (API + cron) · Neon Postgres — all free tier

### Methodology (FAIR-inspired, traceable)
```text
LEF = TEF × Vulnerability
TEF = Contact Frequency × Probability of Action
Vulnerability = Pr(Threat Capability > Resistance Strength)   ← derived, not an input
LM  = Primary Loss + Bernoulli(SLEF) · Secondary Loss

Beta-PERT:  μ = (a+4b+c)/6  ·  α = 1+4(b−a)/(c−a)  ·  β = 1+4(c−b)/(c−a)
Monte Carlo: Poisson(LEF) events → draw magnitudes → sum annual loss
```
- Aligned to **Open Group Open FAIR** (O-RA 2.0.1 / O-RT 3.0.1).
- Seeded & reproducible: same inputs + same seed ⇒ same result.

### Optimization Formulation
```text
maximise   Σ rᵢ · xᵢ            rᵢ = risk removed by control i
subject to Σ cᵢ · xᵢ ≤ B        budget
           x_a ⇒ x_b            prerequisites
           x_m = 1              mandatory controls
           xᵢ ∈ {0,1}
```
- Risk reduction is **submodular** → pairwise-overlap penalty in CP-SAT, then full re-simulation of every candidate portfolio.

**Visual:** left-to-right layered architecture; highlight the two differentiators — *provenance-carrying risk model* and *re-simulated optimizer*.

---

## Slide 4 — Feasibility, Data & Validation

### Data Sources (all free, no paid key)
| Source | Role | Cost |
|---|---|---|
| NVD CVE API 2.0 | vulnerability facts, CVSS | free (optional key) |
| FIRST EPSS | exploitation-likelihood signal | free |
| CISA KEV | confirmed in-the-wild exploitation | free |
| MITRE ATT&CK | technique → scenario linking | free |
| Org telemetry (CSV / Wazuh) | asset & control posture | local |

### What We Have Already Built (verified)
- **Live enrichment:** 18/18 demo CVEs found in NVD → **100% enriched** (CVSS + EPSS + KEV).
- **ATT&CK enterprise:** version 19.2 → **697 techniques**, 44 mitigations.
- **Demo organization** (fictional AICTE campus): 33 assets (16 CRITICAL / 11 HIGH / 6 MEDIUM), 8 services, 3 business units, 11 controls, 24 findings, 8 risk scenarios.
- **Quantitative core proven:** example ransomware scenario (seed 42, 100k trials) → EAL ₹6.32M, P95 ₹19.09M.
- **Story that distinguishes us:** `CVE-2021-44228` sits on **3 assets at 3 different criticality bands** — same CVE, three different rupee exposures.

### Feasibility
- **Technical:** deterministic Python core + open free APIs; no proprietary data needed.
- **Cost:** ₹0 — free-tier hosting + free feeds.
- **Reproducibility:** test suite runs fully offline & deterministic (mocked transports), plus live end-to-end verification.

**Visual:** three cards — *Real data* · *Working core* · *Zero cost*.

---

## Slide 5 — Impact & Benefits

### The Decision It Changes
```text
Budget: ₹25,00,000   →   Where should it go?

Naive highest-CVSS strategy   →  risk reduction [FILL]
Our CP-SAT optimizer          →  risk reduction [FILL]   ✓ (same budget, more risk removed)
```
*Both figures re-simulated on the same harness — not summed additively.*

### Killer Scenario
> **"Implement MFA for all privileged identities."**
```text
Coverage 0% → 100% ;  EAL before ₹[FILL] → after ₹[FILL]
Risk reduction [FILL]%  ·  Cost ₹[FILL]  ·  ROSI-like [FILL]×
```

### Impact
- **For the CISO:** a rupee figure and a ranked portfolio to defend in the board room.
- **For the SME / college:** enterprise-grade CRQ with no licensing cost.
- **For the auditor:** every number traceable to source, date, confidence, and seed.
- **For compliance:** one control catalog mapped to NIST CSF 2.0, CIS v8.1, ISO 27001, RBI, SEBI CSCRF.

### Why It Wins
- Turns **severity → money → spend decision** in one pipeline.
- Honest by design: uncertainty is shown, synthetic inputs are labelled, and every AI-cited figure traces back to the engine.

**Visual:** before/after loss-distribution curves shifting left + the optimizer-vs-baseline bar comparison.

---

## Slide 6 — Roadmap, Demo & Team

### Roadmap (phased, built in the open)
- [x] Phase 0 — Monorepo scaffold + Docker stack
- [x] Phase 1 — Scientific core (Beta-PERT, Monte Carlo, provenance)
- [x] Phase 2 — Live ingestion (NVD / EPSS / KEV / ATT&CK)
- [x] Phase 3 — Business context + demo organization seed
- [ ] Phase 4 — Investment optimizer (CP-SAT + baselines + harness)
- [ ] Phase 5 — Scenario engine + REST API
- [ ] Phase 6 — Frontend dashboards (Next.js + ECharts)
- [ ] Phase 7 — Compliance mapping (NIST / CIS / ISO / RBI / SEBI)
- [ ] Phase 8 — AI layer (Groq tool-calling + trend/anomaly)
- [ ] Phase 9 — Polish, deploy, proof, demo

### Live Demo Flow (5 min)
1. Budget prompt: ₹25L — "CVSS is severity, not risk."
2. `CVE-2021-44228` → CVSS → EPSS → KEV → **3 assets, 3 criticality bands**.
3. Monte Carlo distribution: EAL / P50 / P90 / P95 + **assumptions drawer** (seed, sources, model version).
4. Click **MFA for privileged identities** → distribution shifts left.
5. Run **optimizer** at ₹25L → recommended portfolio vs highest-CVSS baseline.
6. Ask the AI: *"Why not spend the rest on a bigger SIEM?"* → cites optimizer marginals.

### Team
| Name | Role |
|---|---|
| `[NAME]` | Team Leader / Backend & Risk Engine |
| `[NAME]` | Data Ingestion & Normalization |
| `[NAME]` | Optimization & Analytics |
| `[NAME]` | Frontend & Visualization |
| `[NAME]` | AI Layer & Integration |
| `[NAME]` | Research, Compliance Mapping & Docs |

### References
- Open Group **Open FAIR** (O-RA 2.0.1 / O-RT 3.0.1) · NIST CSF 2.0 · NIST SP 800-30 / 800-221 · CIS Controls v8.1 · ISO/IEC 27001 & 27005 · RBI Cyber Security Framework · SEBI CSCRF
- Data: NVD (NIST) · FIRST EPSS · CISA KEV (CC0) · MITRE ATT&CK (© MITRE, used with permission)

**Visual:** roadmap timeline (completed phases in accent colour) + demo flow strip + team photos.

---

## Before You Present — Fill These In
Do **not** put invented figures on Slides 5–6. Run the actual pipeline and record:
- [ ] Optimizer portfolio for ₹25L (which controls, total spend)
- [ ] Risk-reduction % for optimizer and each baseline (CVSS-first, EPSS-first, density-greedy)
- [ ] MFA scenario: EAL before/after, cost, ROSI-like
- [ ] One headline: "₹X of annual risk removed for ₹Y of spend"
