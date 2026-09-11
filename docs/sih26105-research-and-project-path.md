# SIH26105 — Research, Feasibility Analysis & Project Path

## Executive conclusion

**Recommendation: proceed with SIH26105.**

The strongest feasible interpretation of the problem is not “build a complete enterprise cyber-risk platform.” It is:

> **Build a transparent cyber-risk decision engine that converts security findings + business context into an uncertainty-aware financial risk distribution, then chooses the best security investments under a fixed budget and explains why.**

The project should satisfy the full statement through a layered design:

1. **Ingestion and normalization** — vulnerabilities, security events, identities/control posture, asset inventory and optional cloud findings.
2. **Risk quantification** — FAIR-inspired loss-event-frequency / loss-magnitude modelling, using real public vulnerability intelligence where possible and explicit organization-provided assumptions where not.
3. **AI decision support** — risk-driver explanation, trend/anomaly analysis, recommendations and natural-language queries.
4. **Scenario engine** — “what happens if MFA is deployed?”, “what if remediation is delayed 30 days?”, “what if this asset becomes critical?”.
5. **Investment optimizer** — maximize expected risk reduction subject to budget, dependencies, implementation constraints and optional mandatory controls.
6. **Framework mapping** — NIST CSF 2.0, ISO/IEC 27001/27005, CIS Controls v8.1, RBI requirements and SEBI CSCRF.
7. **Executive + technical dashboards** — one system, different views.

The **demo should deliberately use a hybrid evidence model**: live/public vulnerability intelligence (NVD/CVSS/EPSS/CISA KEV) + controlled synthetic enterprise telemetry + explicitly declared financial assumptions. Never present synthetic assumptions as measured industry facts.

---

## 1. The official problem statement, decomposed

SIH26105 is titled **“AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform.”** It is a software problem under the Blockchain & Cybersecurity theme from the **All India Council for Technical Education (Cyber Security Cell)**. The accessible SIH 2026 archive currently lists a submission deadline of **30 September 2026** and identifies the source as SIH 2026. The archive is community-maintained; the page links to the SIH portal as the official source. [1]

The statement has seven practical jobs to perform.

### 1.1 Continuously aggregate technical evidence

The statement names these inputs:

- vulnerability management
- SIEM
- IAM
- EDR
- CSPM
- asset inventory
- threat intelligence
- other security/IT sources

The requirement is therefore an **integration/normalization problem**, not the creation of seven independent security products. [1]

### 1.2 Attach business context

The statement explicitly requires correlation with **business asset criticality** and **control effectiveness**. This is important because vulnerability severity by itself is not organizational risk.

FIRST's CVSS v4 guidance explicitly distinguishes intrinsic vulnerability severity from environmental and threat context, and says Environmental and Threat metrics are applied by the consumer to reflect local context. EPSS similarly warns that its probability is not a complete risk score and must be combined with environmental context and impact. [2][3]

### 1.3 Quantify financial exposure

The statement calls for monetary exposure such as:

- Expected Annual Loss (EAL/ALE-style output)
- Value at Risk (VaR)
- organization-level exposure
- business-unit exposure
- asset-level exposure
- impact components such as downtime, breach costs, regulatory penalties and reputational effects [1]

This is the hardest conceptual component because public data does not let a student team truthfully claim a precise “Indian organization breach cost” for a specific simulated company. The correct engineering response is **uncertainty-aware quantification** rather than fake precision.

### 1.4 Recommend security actions

The statement asks for AI-generated mitigation recommendations, examples including patching, access-control tightening, network segmentation and increased monitoring, each with quantified risk reduction. [1]

### 1.5 Run what-if scenarios

The explicit examples are:

- MFA across privileged accounts
- delaying remediation by 30 days

This is ideal for a live hackathon demo because it produces a visible before/after decision rather than a static dashboard. [1]

### 1.6 Optimize a constrained security budget

The central investment problem is:

> Given a finite security budget, which set of controls/remediations gives the greatest reduction in financial cyber risk?

The statement gives **₹1 crore** as an example budget. [1]

This is the component that can produce a clean, defensible algorithmic result. It can be formulated as a constrained optimization problem rather than as a subjective security score.

### 1.7 Communicate and map the results

The platform must serve technical and executive stakeholders and map risk/control information to:

- ISO/IEC 27001
- NIST Cybersecurity Framework
- CIS Controls
- RBI Cyber Security Framework
- SEBI Cybersecurity and Cyber Resilience Framework [1]

---

# 2. What the problem is really asking for

The problem is best understood as a **translation pipeline**:

```text
SECURITY TELEMETRY
       │
       ▼
NORMALIZATION + ASSET CORRELATION
       │
       ├── vulnerability facts
       ├── exploit/threat signals
       ├── identity/control posture
       ├── endpoint / SIEM evidence
       └── asset & business context
       │
       ▼
CYBER RISK SCENARIOS
       │
       ▼
PROBABILITY + LOSS DISTRIBUTIONS
       │
       ▼
FINANCIAL RISK
(EAL / P90 / P95 / P99 / tail)
       │
       ├───────────────┐
       ▼               ▼
SCENARIO ENGINE     OPTIMIZER
       │               │
       └──────┬────────┘
              ▼
    SECURITY DECISIONS
              │
              ▼
EXECUTIVE + TECHNICAL VIEWS
              │
              ▼
FRAMEWORK / AUDIT MAPPING
```

The important insight is that **the platform does not replace security tooling**. It sits above security tooling as a risk-decision layer.

That positioning is consistent with commercial CRQ products, which generally describe themselves as a layer that consumes security-stack information and turns it into financially expressed risk and prioritization. SAFE, CyberHQ, C-Risk and similar vendors are evidence that this is a real product category rather than an invented hackathon-only concept. [12][13][14]

---

# 3. What existing standards say you should build

## 3.1 NIST CSF 2.0: the governance/communication layer

NIST CSF 2.0 is designed to help organizations understand, assess, prioritize and communicate cybersecurity risk. Its six functions are **Govern, Identify, Protect, Detect, Respond and Recover**. It is intentionally outcome-oriented rather than prescribing one technical implementation. [4][5]

For this project, CSF 2.0 should be used as a **control/outcome taxonomy and reporting lens**, not as the mathematical risk engine.

That distinction matters.

Use:

```text
CSF 2.0 → What outcome/control area does this address?
FAIR-style model → How much risk does the scenario create?
Optimizer → Where should money go?
```

NIST's current CSF 2.0 Informative References program is especially useful because the mappings are machine-readable and include mappings such as ISO/IEC 27001:2022 → CSF 2.0 and CIS Controls 8.1 → CSF 2.0. NIST published the final **SP 1347** Quick-Start Guide for these mappings in August 2026. [5][6]

### Project use

Implement a normalized `control_catalog` with fields such as:

```json
{
  "control_id": "MFA-PRIV-01",
  "name": "MFA for privileged identities",
  "nist_csf": ["PR.AA"],
  "cis": ["6.3"],
  "iso27001": ["A.5", "A.8"],
  "rbi": ["access control"],
  "sebi": ["protect / identity-access control"],
  "evidence": ["iam_config", "mfa_coverage"]
}
```

The exact regulatory clause mapping should be maintained as a curated data table with source/version metadata. Do not let an LLM invent regulatory mappings.

---

## 3.2 NIST SP 800-30: risk assessment discipline

NIST SP 800-30 Rev. 1 provides a structured approach for preparing, conducting and maintaining risk assessments. It explicitly covers risk, threat, vulnerability, residual risk and security controls, and it is intended to provide decision information to organizational leadership. [7]

This supports a project design where each scenario records:

- threat source / threat event
- vulnerable condition
- affected asset
- likelihood estimate
- impact estimate
- existing controls
- residual risk
- proposed treatment

The project should therefore avoid a single opaque “AI risk score.”

---

## 3.3 NISTIR 8286 / 8286A / 8286B: enterprise risk register and prioritization

NISTIR 8286 describes integrating cybersecurity risk into enterprise risk management using a cybersecurity risk register and enterprise risk profile. NISTIR 8286A describes identifying and estimating cybersecurity risk using documented scenarios, likelihood and impact. NISTIR 8286B explicitly addresses **prioritizing cybersecurity risk** and incorporating projected cost of risk response. [8][9][10]

This is almost tailor-made for the project.

Use the risk register as the internal canonical object:

```text
Risk ID
 ├── scenario
 ├── threat
 ├── asset
 ├── vulnerability/condition
 ├── likelihood distribution
 ├── impact distribution
 ├── current controls
 ├── residual risk
 ├── proposed response
 ├── response cost
 ├── owner
 └── framework mappings
```

The enterprise dashboard is then an aggregation of those risk records.

---

## 3.4 NIST SP 800-221: risk portfolio thinking

NIST SP 800-221 focuses on incorporating ICT risk into the broader enterprise risk portfolio and communicating lower-level risks upward into an enterprise risk profile. [11]

This directly supports your hierarchy:

```text
Asset → Business Service → Business Unit → Enterprise
```

Example:

```text
Student portal server
      ↓
Admissions service
      ↓
Academic Operations
      ↓
Institution
```

The same risk can therefore be shown technically and financially at different organizational levels.

---

# 4. Why FAIR is the right quantitative backbone

The Open Group's Open FAIR standards provide a formal taxonomy and process for quantitative information-security risk analysis. The current Open FAIR material describes **O-RA 2.0.1** and **O-RT 3.0.1**, and explicitly positions the approach as usable with other standards and frameworks. It also provides an Open FAIR Risk Analysis Process Guide, Example Guide, mathematics guide and NIST CSF cookbook. [15]

The broad model you should adopt is:

```text
Threat Event Frequency
          ↓
      Vulnerability
          ↓
Loss Event Frequency
          ↓
Loss Magnitude
          ↓
        Risk
```

For a hackathon implementation, do not pretend to recreate every nuance of a professional FAIR assessor's workflow. Instead implement a **FAIR-inspired, traceable quantitative model** and clearly state which inputs are approximations.

## 4.1 Why not use CVSS as the risk engine?

FIRST explicitly states that CVSS Base is a measure of vulnerability severity, not complete risk. CVSS v4 includes Base, Threat, Environmental and Supplemental metric groups. Local environmental and threat context can materially change how useful the score is for a particular organization. [2]

Therefore:

```text
CVSS = technical severity signal
EPSS = observed-exploitation probability signal
KEV = high-confidence exploited-in-the-wild signal
Business context = local impact / importance
Controls = resistance / mitigation context
```

Together they create a much stronger input layer.

---

# 5. Real public data you can actually use

This is how to avoid the biggest criticism of this problem statement: invented telemetry everywhere.

## 5.1 NVD / CVE data

NIST's National Vulnerability Database provides structured vulnerability information. The NVD API/data-feed system is now centered on the **2.0 APIs/data formats**; NIST retired older legacy feed formats beginning in 2025 and expanded the current schema in 2026, including additional structured information such as SSVC and affected-product data. [16]

Use NVD for:

- CVE identifiers
- descriptions
- affected products / CPE information
- CVSS information
- references
- timestamps

This gives the project real technical evidence.

## 5.2 EPSS

FIRST's Exploit Prediction Scoring System provides a daily **0–1 probability** estimate for whether a CVE will be exploited in the wild within the next 30 days. It is explicitly a prioritization signal, not a complete environmental risk score. Data is openly available by API and CSV. [3][17]

This is extremely useful for your project because building your own exploitation-probability model from scratch would be unnecessary and difficult to defend.

Use EPSS as:

```text
Threat / exploitation-likelihood signal
```

not as:

```text
overall enterprise risk score
```

## 5.3 CISA Known Exploited Vulnerabilities

CISA describes its KEV catalog as the authoritative source of vulnerabilities known to have been exploited in the wild and recommends using it as an input to vulnerability-management prioritization. It is available in CSV and JSON. [18]

Use KEV as a binary/weighted threat-evidence feature:

```text
KEV = true → strong evidence of active exploitation relevance
KEV = false → not evidence that exploitation is impossible
```

## 5.4 MITRE ATT&CK

MITRE ATT&CK provides a public knowledge base of adversary tactics and techniques. The Enterprise matrix currently contains 15 tactics, including Initial Access, Credential Access, Lateral Movement, Exfiltration and Impact, and ATT&CK provides downloadable structured data. [19][20]

This enables the project to connect technical findings to attack scenarios:

```text
CVE / misconfiguration
       ↓
ATT&CK technique
       ↓
Attack path / scenario
       ↓
Affected asset / business service
       ↓
Financial consequence
```

This is far better than showing a flat list of CVEs.

---

# 6. The financial model: make the uncertainty visible

The biggest trap is presenting:

> “Your exact cyber risk is ₹4,82,31,000.”

That is fragile because the underlying inputs are not exact.

Instead show:

```text
Annual Cyber Loss Exposure

P10     ₹1.3 Cr
P50     ₹3.8 Cr
P90     ₹8.9 Cr
P95     ₹11.7 Cr

Expected Annual Loss: ₹4.4 Cr
```

and include:

```text
Data confidence: Medium
Main assumptions: 7
External evidence: 4
Organization-provided inputs: 9
Synthetic assumptions: 5
```

The user can then inspect why each distribution looks the way it does.

NIST's current measurement guidance explains VaR as a statistical technique based on a probability distribution over a fixed period and confidence level, and warns that model quality is heavily dependent on input quality. NISTIR 8286C Rev. 1 also notes that enterprise cyber-risk aggregation may be reported using PML/MFL or VaR-style approaches. [21][22]

---

## 6.1 Suggested minimum scenario model

For each scenario define:

### Frequency side

```text
contact_frequency
×
probability_of_action
×
probability_of_success_after_controls
```

This is a simplified operationalization of the FAIR logic.

### Magnitude side

Break the loss into components:

```text
primary_loss =
    incident_response
  + downtime
  + recovery
  + direct fraud / theft
  + data restoration

secondary_loss =
    notification / legal
  + regulatory exposure
  + customer impact
  + reputational / business consequence proxy
```

Do not call these “actual Indian average costs” unless you have an authoritative source for that exact claim.

Instead allow three-point estimates:

```text
minimum
most_likely
maximum
```

and convert them into a PERT/Beta-style distribution for simulation.

---

# 7. Monte Carlo is the practical way to demonstrate uncertainty

A Monte Carlo engine can run thousands of trials per scenario:

```text
For each trial:
    sample frequency
    sample loss magnitude
    sample control effectiveness
    sample correlated factors where appropriate
    compute annual loss

After N trials:
    mean
    median
    P90
    P95
    P99
    loss-exceedance curve
```

This creates the visual evidence that makes the project convincing.

Example UI:

```text
Potential annual loss
₹
│                         ▂▃▄
│                    ▂▅██████
│                ▂▄██████████
│           ▂▃▄██████████████
│      ▂▃▄███████████████████
└─────────────────────────────── Probability
       P50     P90       P99
```

The Open FAIR resource set explicitly includes mathematics guidance and tools for quantitative analysis and probability models. NIST also provides guidance around VaR and risk measurement. [15][21]

---

# 8. Asset criticality model

The statement specifically requires asset criticality to affect risk.

Use an explicit business criticality object rather than a mysterious multiplier:

```text
Asset
 ├── business_service
 ├── owner
 ├── revenue_dependency
 ├── data_sensitivity
 ├── operational_criticality
 ├── regulatory_scope
 ├── internet_exposure
 ├── dependency_count
 └── recovery_time_objective
```

A practical 1–5 criticality scale is enough for the demo, but the weighting should be visible.

Example:

| Attribute | Example scale |
|---|---:|
| Availability criticality | 1–5 |
| Integrity criticality | 1–5 |
| Confidentiality criticality | 1–5 |
| Regulatory relevance | 0–5 |
| Internet exposure | 0–5 |
| Dependency centrality | 0–5 |

Do not automatically multiply everything together. That can create absurd nonlinear effects. Use a documented weighting model or a calibrated score that feeds the scenario parameters.

---

# 9. Control-effectiveness model

The statement specifically asks for control effectiveness based on configuration strength, incident history and compliance status. [1]

Represent a control with evidence rather than a simple yes/no field:

```text
Control: Privileged MFA

coverage = 82%
configuration_strength = 0.91
recent_incident_signal = 0.20
policy_compliance = 0.95
verification_age_days = 17
```

Then calculate a bounded effectiveness estimate.

A simple demo version could be:

```text
control_effectiveness
  = weighted evidence score
```

Then use effectiveness to reduce scenario parameters rather than claiming it directly predicts loss.

Example:

```text
before MFA:
    success probability distribution = high

after MFA:
    success probability distribution = lower
```

This becomes visible in the scenario comparison.

---

# 10. Investment optimization is your strongest technical differentiator

This should be the centerpiece of the project.

## 10.1 Formal problem

Let each candidate remediation `i` have:

- `cost_i`
- `risk_reduction_i`
- framework coverage
- prerequisites
- implementation time
- operational impact

Then solve:

```text
maximize     total risk reduction
subject to   Σ cost_i x_i ≤ budget
             x_i ∈ {0,1}
             prerequisite constraints
             mandatory-control constraints
```

The subtle part is that risk reductions are not always additive because two controls may overlap.

Therefore, for the more mature version, evaluate the combined portfolio by re-running the risk model after applying all selected controls:

```text
Portfolio A
  ↓
Risk simulation
  ↓
Exposure reduction

Portfolio B
  ↓
Risk simulation
  ↓
Exposure reduction
```

For small demo problem sizes, brute-force or exact integer optimization is perfectly feasible.

For more general constraints, Google's OR-Tools CP-SAT is a practical open-source solver. Google recommends CP-SAT for many constraint-programming tasks and provides official documentation and examples. [23]

---

# 11. Make the optimizer beat a naive baseline

This is critical for a convincing judge demo.

Build two strategies:

### Baseline

```text
Sort vulnerabilities by CVSS.
Patch highest score first until budget is exhausted.
```

### Your optimizer

```text
Evaluate business context + exploitation signals + control gaps + financial impact.
Choose the portfolio with maximum modeled risk reduction under budget.
```

Then display:

| Strategy | Spend | Expected loss | Reduction |
|---|---:|---:|---:|
| Highest CVSS first | ₹10L | ₹4.9Cr | 18% |
| Your optimizer | ₹9.7L | ₹3.2Cr | 46% |

**The numbers in a demo must be clearly marked as model outputs from the demonstration environment.**

The point being proven is the decision logic, not that the exact ₹ figure describes a real enterprise.

This directly aligns with NIST's cost-effective, risk-based control selection and earlier NIST work on analytical approaches to cybersecurity budgeting. NISTIR 7385 describes using structured multi-attribute decision methods to select cost-effective security investments under constraints. [24]

---

# 12. ROI / ROSI

A security-ROI calculation should be framed as **risk reduction value**, not “security makes money.”

One defensible hackathon metric is:

```text
Risk reduction value
  = baseline expected annual loss
  − post-control expected annual loss
```

Then:

```text
ROSI-like metric
  = (risk reduction value − annualized control cost)
    / annualized control cost
```

Also show:

```text
₹ risk removed per ₹ spent
```

Example:

```text
MFA
Cost: ₹3.0L
Annual loss reduction: ₹11.5L
Risk removed / ₹ spent: 3.83x
```

Use “ROSI-like” or define your exact formula rather than implying that your metric is a universal accounting standard.

SAFE's commercial ROSI calculator demonstrates that security-investment return is already a commercial CRQ use case and explicitly describes API-driven data collection and real-time prioritization of cost-effective cybersecurity investments. [12]

---

# 13. Scenario simulation design

Scenario simulation should operate on a copy of the current risk state:

```text
Current state
     │
     ├── Apply scenario change
     │      ├── enable MFA
     │      ├── patch CVE
     │      ├── segment network
     │      ├── improve EDR coverage
     │      └── delay remediation
     │
     ▼
Recalculate risk
     │
     ▼
Compare distributions
```

The UI should show:

```text
CURRENT                  SCENARIO
EAL: ₹4.4Cr              EAL: ₹2.8Cr
P90: ₹9.2Cr              P90: ₹5.8Cr

Risk reduction: 36%
Cost: ₹6.4L
ROSI-like: 1.5x
```

### Killer scenario

Use the statement's own example:

> **“What happens if MFA is implemented across all privileged accounts?”**

Click button → update control coverage → rerun simulation → show the distribution shifting left → show updated optimizer recommendations.

---

# 14. Continuous risk: make it real enough for the demo

You do not need live enterprise SIEM feeds to demonstrate continuous risk.

Use a **two-mode ingestion architecture**.

## Mode A — real/public evidence

Pull periodically:

- NVD/CVE data
- EPSS
- CISA KEV

This provides genuine changing threat/vulnerability evidence. [3][16][18]

## Mode B — organization/simulator telemetry

Provide a local JSON/CSV schema for:

- asset inventory
- vulnerability findings
- IAM/MFA coverage
- EDR coverage
- endpoint health
- SIEM indicators
- cloud findings
- control status

Then provide a **“stream simulator”** which changes selected fields every 15–30 seconds in the demo:

```text
T0 → critical CVE appears
T1 → KEV flag becomes active
T2 → EDR coverage drops
T3 → privileged MFA coverage increases
T4 → risk recalculates
```

The dashboard visibly changes without requiring privileged access to a real corporation.

This satisfies the conceptual “continuous” requirement without pretending your university has a Fortune 500 SOC wired into your project.

---

# 15. Wazuh is a very practical optional integration

If the team wants a real security telemetry source, Wazuh is a strong option for the demonstration environment.

Wazuh's documentation says its agent collects software inventory and the Vulnerability Detection capability correlates installed packages with vulnerability information. Its system inventory is continuously updated on monitored endpoints, and its vulnerability detection can run with periodic feed updates. [25][26][27]

That makes Wazuh a plausible real lab source for:

```text
Endpoint
  ↓
Wazuh agent
  ↓
Inventory / alerts
  ↓
Normalization adapter
  ↓
Your CRQ engine
```

Do not make Wazuh a hard dependency for the hackathon demo. Build a replay/synthetic adapter too, so a missing agent cannot kill the presentation.

---

# 16. AI/ML: what to actually build

Do not train a giant “cyber risk AI” model.

That will consume time and provide weak scientific justification.

Instead, split deterministic analytics from AI.

## 16.1 Deterministic core

The following should be deterministic:

- CVSS interpretation
- EPSS/KEV ingestion
- asset criticality calculations
- control-effectiveness scoring
- Monte Carlo simulation
- investment optimization
- framework mappings
- ROI calculations

A judge should be able to inspect the equations.

## 16.2 AI components

### A. Risk-driver explanation

Given the top contributors, generate a plain-language explanation:

> “The Admissions API is currently the largest contributor because it combines an internet-facing asset, a high-impact vulnerability, elevated exploitation probability and weak privileged-access controls.”

The underlying facts should come from your structured engine; the LLM is only converting those facts into human language.

### B. Natural-language query layer

Examples:

```text
What is our highest financial cyber risk?

Which assets contribute most to P90 loss?

What can we do with ₹25 lakh?

What happens if we delay patching for 30 days?

Why is MFA recommended before SIEM expansion?
```

The LLM should call tools/functions that query the risk engine. It should not calculate regulatory rules or invent risk figures in free-form text.

### C. Recommendation ranking

The optimizer already produces candidate control portfolios. AI can explain:

```text
Recommendation
Why
Expected reduction
Cost
Dependencies
Mapped controls
Confidence / evidence quality
```

### D. Optional trend/anomaly model

A lightweight model can detect abnormal changes in:

- vulnerability counts
- KEV exposure
- MFA coverage
- EDR coverage
- incident volume
- mean time to remediate

This is enough to honestly justify the AI-powered label.

---

# 17. Framework mapping: use a normalized control ontology

Do not build five independent compliance modules.

Build one internal ontology:

```text
Internal Control
     │
     ├── NIST CSF 2.0
     ├── CIS v8.1
     ├── ISO/IEC 27001:2022
     ├── RBI requirement
     └── SEBI CSCRF requirement
```

NIST CSF 2.0's Informative References tooling is especially useful because it provides machine-readable crosswalk data and explicitly lists ISO/IEC 27001:2022 and CIS Controls 8.1 mappings. [5][6]

CIS itself describes v8.1 as mapped to multiple frameworks, and its v8.1 update specifically realigned NIST mappings to CSF 2.0 and introduced governance alignment. [28]

### Regulatory mapping strategy

Treat RBI and SEBI as **Indian regulatory overlays**, not just aliases for NIST.

RBI's 2023 IT Governance, Risk, Controls and Assurance Practices Directions include areas such as risk assessment, vulnerability assessment/penetration testing, cyber incident response and recovery, access controls, audit trails, metrics, change/patch management and IT/security risk management. The same direction explicitly says cybersecurity budget should be determined with the current/emerging threat landscape in mind. [29]

SEBI's Cybersecurity and Cyber Resilience Framework (CSCRF) defines governance and the familiar Identify/Protect/Detect/Respond/Recover structure, uses a graded approach for different types/scales of regulated entities, and has subsequent clarification/extension circulars. [30][31][32]

The CSCRF should therefore be represented with **versioned regulatory data**.

---

# 18. India-specific regulatory context

## 18.1 RBI

The RBI Master Direction on IT Governance, Risk, Controls and Assurance Practices, issued November 7, 2023, consolidates and updates guidance around IT governance, controls, assurance and business continuity/disaster recovery. It contains a dedicated risk-assessment chapter and requirements around vulnerability assessment/penetration testing and cyber incident response/recovery. [29]

This is valuable to your project because it creates a strong Indian use case for:

```text
security posture
      ↓
risk assessment
      ↓
control gaps
      ↓
budget priority
      ↓
board/CISO review
```

## 18.2 SEBI

SEBI issued CSCRF in August 2024 and later issued clarification/technical clarification and implementation-related circulars in 2024–2025. SEBI's published framework describes six cybersecurity functions: Governance, Identify, Protect, Detect, Respond and Recover. [30][31][32]

## 18.3 CERT-In

CERT-In maintains its Directions under Section 70B of the IT Act, including the April 28, 2022 directions relating to information-security practices, prevention, response and reporting of cyber incidents. CERT-In's own auditing guidance emphasizes translating technical findings into relevant business risks and explicitly references compliance with those directions. [33][34]

CERT-In is a useful **reporting/governance context** for the platform, although it is not one of the exact mappings named in the SIH statement.

## 18.4 DPDP

The Digital Personal Data Protection Act, 2023 is an important India-specific data-governance context where personal data is involved. The official India Code record identifies the Act, and MeitY published the Digital Personal Data Protection Rules, 2025 and an enforcement timeline in November 2025. [35][36]

For the project, do not turn DPDP into another massive compliance module. Use it as a data-impact input and regulatory-exposure context where a scenario affects personal data.

---

# 19. A defensible data-confidence model

This is a major opportunity to make the project look mature.

Every risk output should carry a confidence/evidence score.

Example:

```text
Financial Exposure: ₹4.4 Cr EAL
Evidence confidence: 72%

Evidence mix:
  Public vulnerability intelligence: 35%
  Observed environment telemetry:   40%
  Organization estimates:            15%
  Synthetic/demo assumptions:        10%
```

Or use qualitative confidence:

```text
HIGH
MEDIUM
LOW
```

with a drill-down.

This directly addresses the criticism that financial cyber quantification can become “precise numbers built from uncertain assumptions.” The project should make the uncertainty a visible feature rather than hide it.

---

# 20. Competitive landscape and what NOT to copy

There is already a commercial cyber-risk-quantification market.

Examples found in current public materials:

- **SAFE** markets cyber risk quantification and a ROSI calculator that uses security-tool data and prioritizes cost-effective investments. [12]
- **C-Risk / SAFE One** markets FAIR-based financial quantification, control prioritization and ROI-based risk treatment. [13][14]
- **CyberHQ** markets financial cyber risk, scenario/project modeling, and continuous integration with security tools. [15]
- Other CRQ products and newer vendors similarly emphasize FAIR, Monte Carlo, financial exposure and board communication. [37][38]

Therefore, “dashboard that shows a rupee risk score” is **not enough differentiation**.

### Your differentiation should be:

> **Open-data-driven, transparent, reproducible security-investment optimization with inspectable assumptions and an optimizer-vs-baseline demonstration.**

A judge should be able to ask:

> “Why did your system recommend MFA instead of buying another SIEM module?”

and your system should answer with a chain like:

```text
MFA
 ↓
reduces privileged-account attack success probability
 ↓
affects 4 scenarios
 ↓
2 of those scenarios hit critical assets
 ↓
₹X expected annual loss removed
 ↓
₹Y implementation cost
 ↓
3.4x risk-reduction-per-rupee
 ↓
best portfolio under current budget
```

That is far more compelling than “AI score = 83.”

---

# 21. Recommended product architecture

## 21.1 Frontend

Recommended:

```text
React / Next.js
TypeScript
Tailwind or a simple component library
ECharts / Recharts / Plotly
```

Required screens:

1. Executive dashboard
2. Risk explorer
3. Asset/service drill-down
4. Scenario simulator
5. Investment optimizer
6. Control/compliance mapper
7. Technical findings view
8. Assumptions/evidence drawer

## 21.2 Backend

Recommended:

```text
Python
FastAPI
PostgreSQL
Redis (optional)
Pydantic
```

Python is a natural fit because the core needs statistics, optimization and data processing.

## 21.3 Analytics layer

```text
NumPy
Pandas/Polars
SciPy
OR-Tools
```

Optional:

```text
scikit-learn
XGBoost / LightGBM
```

only if a genuine learning component is useful.

## 21.4 AI layer

Use a tool-calling LLM interface:

```text
LLM
 │
 ├── get_top_risks()
 ├── run_scenario()
 ├── optimize_budget()
 ├── explain_control()
 └── get_framework_mapping()
```

Never let the LLM be the system of record for numeric outputs.

## 21.5 Data layer

```text
PostgreSQL
 ├── organizations
 ├── business_units
 ├── services
 ├── assets
 ├── findings
 ├── vulnerabilities
 ├── controls
 ├── control_evidence
 ├── scenarios
 ├── loss_models
 ├── simulations
 ├── investments
 └── framework_mappings
```

---

# 22. Suggested canonical data model

```text
Organization
    │
    ├── BusinessUnit
    │       │
    │       └── Service
    │               │
    │               └── Asset
    │                       │
    │                       ├── Vulnerability
    │                       ├── SecurityFinding
    │                       └── ControlEvidence
    │
    ├── RiskScenario
    │       ├── FrequencyModel
    │       ├── MagnitudeModel
    │       └── LossDistribution
    │
    ├── InvestmentOption
    │       ├── Cost
    │       ├── ControlsAffected
    │       ├── Prerequisites
    │       └── RiskReductionModel
    │
    └── FrameworkMapping
```

Each simulation should be reproducible from:

```text
scenario_version
model_version
input_snapshot
random_seed
simulation_count
```

This is a surprisingly valuable feature for a hackathon because a judge can rerun the same calculation and obtain the same displayed result.

---

# 23. Demo environment that is actually feasible

Do **not** try to create a full enterprise replica.

Build one fictional but realistic organization, such as:

> **AICTE Institute / University digital campus**

with 25–50 assets.

### Example asset groups

```text
Internet-facing
  ├── admissions portal
  ├── student portal
  ├── VPN gateway
  └── email gateway

Internal
  ├── ERP
  ├── HR database
  ├── finance database
  ├── file server
  └── identity provider

Cloud
  ├── application cluster
  ├── object storage
  └── database
```

### Example controls

```text
MFA
EDR
Patch management
Network segmentation
WAF
Privileged access management
Backup / recovery
SIEM monitoring
Email security
Cloud posture management
```

### Example risk scenarios

Keep it to 6–10 scenarios:

1. Ransomware through exposed endpoint
2. Credential compromise of privileged account
3. Web-server vulnerability exploitation
4. Cloud storage/data exposure
5. Database outage / destructive attack
6. Phishing → account takeover
7. Lateral movement from workstation to critical server
8. Third-party/service-provider compromise

---

# 24. The 5-minute judge demo

This is the recommended presentation flow.

## Minute 0:00–0:30 — establish the decision

Show:

```text
Cybersecurity Budget: ₹25 Lakh

Question:
Where should the next ₹25L go?
```

Then show a conventional vulnerability dashboard with high/medium/low findings.

Say:

> “CVSS tells us severity. It does not tell us which investment removes the most business risk.”

Do not attack CVSS unfairly; say it is one input, not the entire risk model. FIRST explicitly makes this distinction. [2]

## Minute 0:30–1:30 — evidence

Show:

- actual CVE identifiers
- CVSS
- EPSS
- KEV status
- affected asset
- asset criticality
- control posture

Click one finding.

Show:

```text
CVE → exploit signal → asset → business service → scenario
```

## Minute 1:30–2:30 — financial risk

Show Monte Carlo distribution:

```text
EAL: ₹X
P50: ₹Y
P90: ₹Z
```

Open assumptions.

Show that the number is a distribution and state that the demo uses synthetic financial assumptions for the fictional environment.

## Minute 2:30–3:30 — the killer scenario

Click:

> “Implement MFA for all privileged identities.”

The distribution shifts.

Show:

```text
EAL before → EAL after
P90 before → P90 after
Risk reduction → XX%
Cost → ₹Y
```

## Minute 3:30–4:30 — budget optimization

Run:

```text
Budget = ₹25L
```

Show:

```text
Recommended Portfolio
✓ MFA
✓ Critical patch wave
✓ Network segmentation
✓ Backup hardening

Spend: ₹23.8L
Risk reduction: 42%
```

Then compare with:

```text
Naive highest-CVSS strategy
Risk reduction: 19%
```

## Minute 4:30–5:00 — board question

Ask the natural-language layer:

> “Why are we not spending the remaining budget on a larger SIEM deployment?”

The answer should cite the actual optimizer result:

> “At the current posture, the marginal annual-risk reduction from SIEM expansion is lower than that of the remaining patch/MFA/network-segmentation options.”

This ends on the business decision, which is exactly what the statement wants.

---

# 25. MVP vs full solution

## MVP — mandatory

Build these first:

```text
[1] Asset inventory
[2] Vulnerability ingestion
[3] NVD + EPSS + KEV enrichment
[4] Asset criticality
[5] Control effectiveness
[6] 6–10 risk scenarios
[7] Monte Carlo financial model
[8] EAL + P90/P95/P99
[9] Scenario simulation
[10] Budget optimizer
[11] Executive dashboard
[12] Technical drill-down
[13] Core framework mapping
```

## Strong differentiator

```text
[14] Optimizer vs CVSS-first baseline
[15] Evidence/confidence model
[16] Reproducible simulation seeds
[17] Natural-language query layer
```

## Stretch features

Only after the above works:

```text
[18] Wazuh live integration
[19] SIEM event correlation
[20] IAM integration
[21] CSPM adapter
[22] ML trend/anomaly detection
[23] Automated report generation
[24] Multi-organization tenancy
```

Do not invert this order.

---

# 26. Build order

## Phase 1 — scientific core

Build the risk model without a dashboard.

Deliver:

```text
scenario.json
risk_model.py
monte_carlo.py
optimizer.py
```

Test using 3–4 scenarios.

## Phase 2 — data enrichment

Add:

```text
NVD
EPSS
KEV
MITRE ATT&CK
```

and normalize them to your internal model.

## Phase 3 — organization simulator

Create:

```text
25–50 assets
6–10 scenarios
8–12 controls
```

Make every asset and assumption traceable.

## Phase 4 — scenario engine

Implement:

```text
clone_state()
apply_control()
apply_delay()
recalculate()
compare()
```

## Phase 5 — optimizer

Start with exact enumeration for small candidate sets.

Then add OR-Tools/CP-SAT if the constraint model becomes richer. [23]

## Phase 6 — UI

Only after the numbers are stable.

## Phase 7 — AI

Expose the existing engine through tool/function calls.

## Phase 8 — live/replay integration

Add Wazuh or another source as a demonstration adapter; keep the simulator as a fallback. [25][26]

---

# 27. How to keep the math honest

Every number displayed by the UI should have a provenance label:

```text
Source type:
  PUBLIC_DATA
  OBSERVED_TELEMETRY
  USER_INPUT
  MODEL_ESTIMATE
  SYNTHETIC_DEMO
```

Each numeric model parameter should store:

```text
value
unit
source
source_date
confidence
assumption_description
model_version
```

Then a judge can click “₹8.9Cr P90” and see:

```text
Derived from:
- 7 risk scenarios
- 10,000 simulation iterations each
- NVD CVE data
- EPSS scores
- CISA KEV evidence
- asset criticality inputs
- control evidence
- synthetic loss estimates for demo environment
```

This is the correct answer to the “you invented the loss numbers” criticism:

> **Yes, some demo inputs are synthetic, and the product explicitly tells you which ones are synthetic. The methodology is deterministic, the assumptions are inspectable, and real security evidence is used where public data exists.**

That is much stronger than pretending otherwise.

---

# 28. Testing strategy

You need more than unit tests for the API.

## 28.1 Mathematical tests

Examples:

```text
If all controls are disabled:
    risk should not be lower than baseline.

If a control strictly reduces a scenario parameter:
    scenario risk should not increase solely because of that control.

If budget = 0:
    optimizer selects no optional control.

If budget ≥ sum(all candidate costs):
    optimizer may select all eligible controls.
```

## 28.2 Monotonicity tests

Very useful:

```text
increase asset criticality
    → risk should not decrease

increase exploit evidence
    → risk should not decrease

increase control coverage
    → affected risk should generally decrease
```

## 28.3 Regression scenario

Freeze one demonstration environment and store:

```text
seed = 42
```

Then ensure the same inputs reproduce the same result.

## 28.4 Optimizer comparison

Run many randomized portfolios and verify:

```text
optimizer_result >= baseline_result
```

for the same budget and assumptions where the model says the optimizer should dominate.

---

# 29. Important modelling caveats

## 29.1 Do not equate “not in KEV” with “not exploitable”

CISA's KEV catalog is a strong evidence source for known exploited vulnerabilities, but absence from KEV is not evidence of zero exploitation risk. EPSS has the same conceptual limitation in a different form. [3][18]

## 29.2 Do not equate CVSS with financial risk

FIRST explicitly distinguishes vulnerability severity from environmental/threat-informed risk. [2]

## 29.3 Do not claim actuarial truth

Your project is a risk-decision model, not an insurance actuarial study.

## 29.4 Do not use an LLM to make up numbers

All financial numbers should originate from a structured model.

## 29.5 Do not use “AI” as decoration

The AI part should explain, query, rank or detect change. The mathematical engine should remain auditable.

---

# 30. Why the project is feasible

The full wording sounds enterprise-sized because it lists many integrations. A student team does **not** need to implement enterprise versions of every tool.

A feasible hackathon implementation is:

```text
Real public security intelligence
+
Controlled synthetic organization telemetry
+
Quantitative risk engine
+
Monte Carlo
+
Optimization
+
Interactive dashboard
+
AI explanation / query layer
+
Versioned framework mapping
```

That is enough to demonstrate the core of every major requirement.

The most time-consuming integrations can be represented by a common adapter interface:

```python
class TelemetryAdapter:
    def fetch_assets(self): ...
    def fetch_findings(self): ...
    def fetch_controls(self): ...
    def fetch_events(self): ...
```

Then:

```text
NVDAdapter
CSVAdapter
WazuhAdapter
SyntheticAdapter
```

all produce the same normalized schema.

That is a much more sensible engineering design than writing six unrelated pipelines.

---

# 31. Recommended differentiation statement

A strong project positioning line is:

> **“We built an explainable cyber-risk investment engine that uses real vulnerability intelligence and organization-specific context to estimate financial exposure, simulate control changes, and select the security portfolio that gives the highest modeled risk reduction per rupee.”**

A stronger technical tagline is:

> **“From CVE to ₹ impact to optimal security spend.”**

---

# 32. Suggested internal modules

```text
crq-platform/
│
├── ingestion/
│   ├── nvd.py
│   ├── epss.py
│   ├── kev.py
│   ├── mitre.py
│   ├── csv_adapter.py
│   └── wazuh.py
│
├── normalization/
│   ├── assets.py
│   ├── findings.py
│   ├── controls.py
│   └── taxonomy.py
│
├── risk/
│   ├── scenarios.py
│   ├── frequency.py
│   ├── magnitude.py
│   ├── monte_carlo.py
│   └── aggregation.py
│
├── optimization/
│   ├── candidates.py
│   ├── baseline.py
│   ├── solver.py
│   └── portfolio.py
│
├── compliance/
│   ├── nist_csf.py
│   ├── cis.py
│   ├── iso27001.py
│   ├── rbi.py
│   └── sebi.py
│
├── ai/
│   ├── tools.py
│   ├── explanations.py
│   ├── query.py
│   └── trends.py
│
├── api/
│   └── main.py
│
└── web/
    └── dashboard/
```

---

# 33. Final scope recommendation

### Build this fully

**Risk decision engine:**

```text
NVD + EPSS + KEV
        ↓
Asset/business context
        ↓
Control effectiveness
        ↓
Scenario modelling
        ↓
Monte Carlo
        ↓
EAL + P90/P95/P99
        ↓
Scenario comparison
        ↓
Budget optimization
        ↓
Executive decision
```

### Build enough of the rest to prove the architecture

```text
SIEM      → normalized adapter + sample events
IAM       → MFA/control coverage dataset
EDR       → coverage/posture dataset
CSPM      → cloud finding adapter
Inventory → real working data model
Threat    → EPSS/KEV/MITRE
```

### Do not attempt for the first milestone

```text
Full enterprise connector marketplace
Full real-time distributed ingestion
Full actuarial calibration
Training a proprietary foundation model
All clauses of all Indian regulations
```

Those are time traps.

---

# 34. What I would consider a winning implementation

A winning version is not the one with the most screens.

It is the version where a judge can do this:

```text
1. Change an asset from medium → critical.
2. See risk increase.
3. Turn MFA coverage from 0% → 100%.
4. See the distribution shift.
5. Give the optimizer ₹25L.
6. See the recommended portfolio.
7. Compare it to CVSS-first remediation.
8. Ask “Why?” in natural language.
9. Open the assumptions behind the financial figure.
10. Open the exact framework mappings.
```

That is a complete story from **telemetry → risk → money → decision → governance**.

---

# 35. Recommended project success metrics

Use measurable technical KPIs in the final presentation:

| KPI | Target |
|---|---:|
| Public CVE enrichment success | >95% for demo dataset |
| Risk calculation reproducibility | 100% with fixed seed |
| Scenario recalculation | <3 sec for demo tenant |
| Budget optimization | <2 sec for 20–40 candidate actions |
| Baseline comparison | present for every demo run |
| Risk-driver explanation | linked to structured facts |
| Framework mapping provenance | 100% of displayed mappings sourced/versioned |
| Synthetic-data disclosure | 100% of synthetic financial assumptions labeled |

These metrics are project-quality metrics, not claims about production enterprise performance.

---

# 36. References and sites

## Problem statement / SIH

**[1] SIH26105 — AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform.** Community-maintained SIH 2026 problem-statement archive; the page identifies AICTE Cyber Security Cell as the organization and links to the official SIH portal.

- https://sih2026.vuce.in/ps/SIH26105
- Official SIH portal link referenced from the archive: https://sih.gov.in/sih2026PS

## Vulnerability and threat intelligence

**[2] FIRST — Common Vulnerability Scoring System (CVSS) v4.0.** Official standard and user guidance.

- https://www.first.org/cvss/v4.0/
- https://www.first.org/cvss/v4.0/user-guide

**[3] FIRST — Exploit Prediction Scoring System (EPSS).** Current methodology, data/API, FAQ and research.

- https://www.first.org/epss/
- https://www.first.org/epss/faq
- https://www.first.org/epss/how-it-works.html

**[18] CISA — Known Exploited Vulnerabilities Catalog.** Official KEV catalog.

- https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**[16] NIST — National Vulnerability Database / NVD updates.** Current API/data-feed transition and schema updates.

- https://www.nist.gov/itl/nvd

**[19] MITRE ATT&CK — Enterprise Tactics.** Public adversary tactics knowledge base.

- https://attack.mitre.org/tactics/enterprise/

**[20] MITRE ATT&CK — Data & Tools.** Structured downloadable ATT&CK data.

- https://attack.mitre.org/resources/attack-data-and-tools/

## Risk management and quantification

**[4] NIST — Cybersecurity Framework (CSF) 2.0.**

- https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20

**[5] NIST — CSF 2.0 Informative References.** Machine-readable crosswalk ecosystem.

- https://www.nist.gov/cyberframework/informative-references

**[6] NIST SP 1347 — Cybersecurity Framework 2.0 Informative References Quick-Start Guide.** Final 2026 edition.

- https://csrc.nist.gov/pubs/sp/1347/final

**[7] NIST SP 800-30 Rev. 1 — Guide for Conducting Risk Assessments.**

- https://csrc.nist.gov/pubs/sp/800/30/r1/final

**[8] NISTIR 8286 — Integrating Cybersecurity and Enterprise Risk Management.**

- https://csrc.nist.gov/Pubs/ir/8286/Final

**[9] NISTIR 8286A Rev. 1 — Identifying and Estimating Cybersecurity Risk for Enterprise Risk Management.** Current 2025/2026 version.

- https://www.nist.gov/publications/identifying-and-estimating-cybersecurity-risk-enterprise-risk-management-0

**[10] NISTIR 8286B — Prioritizing Cybersecurity Risk for Enterprise Risk Management.**

- https://csrc.nist.gov/pubs/ir/8286/b/final

**[11] NIST SP 800-221 — Enterprise Impact of ICT Risk.**

- https://csrc.nist.gov/pubs/sp/800/221/final

**[15] The Open Group — Open FAIR Body of Knowledge.** O-RA, O-RT, methodology guides, examples and tool ecosystem.

- https://www.opengroup.org/open-fair
- https://www.opengroup.org/forum/security/riskanalysis

**[21] NIST SP 800-55 Vol. 1 — Measurement Guide for Information Security.** Includes discussion of Value at Risk.

- https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=958991

**[22] NISTIR 8286C Rev. 1 — Staging Cybersecurity Risks for ERM and Governance Oversight.** Discusses enterprise aggregation and PML/VaR context.

- https://nvlpubs.nist.gov/nistpubs/ir/2025/NIST.IR.8286Cr1.pdf

**[24] NISTIR 7385 — An Analytical Approach to Cost-Effective, Risk-Based Budgeting for Federal Information System Security.**

- https://www.nist.gov/publications/analytical-approach-cost-effective-risk-based-budgeting-federal-information-system

## Security control frameworks

**[28] Center for Internet Security — CIS Controls v8.1.**

- https://www.cisecurity.org/controls/v8-1
- https://www.cisecurity.org/insights/white-papers/cis-controls-v8-1-mapping-to-nist-csf-2-0

**[4][5] NIST CSF 2.0 mapping resources** are especially useful for building the internal control ontology.

**[ISO] ISO/IEC 27001:2022 — Information security management systems.**

- https://www.iso.org/standard/27001.html

**[ISO] ISO/IEC 27005:2022 — Guidance on managing information security risks.**

- https://www.iso.org/standard/80585.html

## India-specific regulatory material

**[29] RBI — Master Direction on Information Technology Governance, Risk, Controls and Assurance Practices, 2023.** RBI/2023-24/107.

- https://systemhealth.rbi.org.in/Scripts/BS_ViewMasDirections.aspx_id%3D12562%283%29.html

**[30] SEBI — Cybersecurity and Cyber Resilience Framework (CSCRF) for SEBI Regulated Entities, August 20, 2024.**

- https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html

**[31] SEBI — Clarifications to CSCRF, December 31, 2024.**

- https://www.sebi.gov.in/legal/circulars/dec-2024/clarifications-to-cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_90401.html

**[32] SEBI — Technical Clarifications to CSCRF, August 28, 2025.**

- https://www.sebi.gov.in/legal/circulars/aug-2025/technical-clarifications-to-cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_96329.html

**[33] CERT-In — Directions under Section 70B.**

- https://www.cert-in.org.in/Directions70B.jsp

**[34] CERT-In — cybersecurity audit ecosystem guidance.**

- https://www.cert-in.org.in/s2cMainServlet?CACODE=CICA-2024-3329&pageid=PUBADV01

**[35] India Code — Digital Personal Data Protection Act, 2023.**

- https://www.indiacode.nic.in/indiacode/handle/123456789/22037?view_type=browse

**[36] MeitY — Digital Personal Data Protection Rules, 2025 and enforcement timeline.**

- https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025%3B

## Telemetry / implementation references

**[25] Wazuh — Vulnerability Detection.**

- https://documentation.wazuh.com/current/user-manual/capabilities/vulnerability-detection/index.html

**[26] Wazuh — How Vulnerability Detection Works.**

- https://documentation.wazuh.com/current/user-manual/capabilities/vulnerability-detection/how-it-works.html

**[27] Wazuh — Configuration / feed update behavior.**

- https://documentation.wazuh.com/current/user-manual/capabilities/vulnerability-detection/configuring-scans.html

**[23] Google OR-Tools — Constraint Solver / CP-SAT.**

- https://developers.google.com/optimization/cp/cp_solver
- https://developers.google.com/optimization/support/cite

## Commercial / competitive references

**[12] SAFE — ROSI Calculator.** Demonstrates that quantified risk-reduction-per-investment is an established commercial CRQ use case.

- https://safe.security/resources/press-release/rosi-calculator-launch/

**[13] SAFE / C-Risk — Cyber Risk Officer / financial cyber risk.**

- https://safe.security/solutions/cro/

**[14] C-Risk — SAFE One / Cyber Risk Quantification.**

- https://www.c-risk.com/crq-platform

**[37] CyberHQ — Cyber Risk Quantification and Scenario/Project Modeling.**

- https://www.avertro.com/solutions/use-cases/cyber-risk-quantification
- https://www.avertro.com/cyberhq/cyber-risk-quantification-decision-intelligence

**[38] Current CRQ vendor example — TRNEOPS.** Useful as a competitive reference for Indian rupee-denominated CRQ positioning; treat vendor claims as marketing, not independent evidence.

- https://trneops.com/

---

# 37. Final recommended roadmap

## Milestone 1 — Core model

**Goal:** one scenario → one loss distribution → one EAL.

Deliverables:

```text
FAIR-inspired scenario model
Monte Carlo
P50/P90/P95/P99
Assumption/provenance system
```

## Milestone 2 — Real evidence

**Goal:** make the model consume real vulnerability intelligence.

Deliverables:

```text
NVD
CVSS
EPSS
CISA KEV
MITRE ATT&CK
```

## Milestone 3 — Business context

**Goal:** show why the same CVE matters differently on different assets.

Deliverables:

```text
asset criticality
service dependency
control effectiveness
```

## Milestone 4 — Optimization

**Goal:** turn the project into an investment engine.

Deliverables:

```text
candidate controls
budget constraint
portfolio optimizer
baseline comparison
ROSI-like metrics
```

## Milestone 5 — Demo-quality scenario engine

**Goal:** create an unforgettable interaction.

Deliverables:

```text
MFA scenario
30-day remediation delay
before/after distributions
investment-vs-risk curve
```

## Milestone 6 — Governance

**Goal:** satisfy the framework/regulatory side without drowning in compliance work.

Deliverables:

```text
NIST CSF 2.0
CIS v8.1
ISO 27001/27005
RBI
SEBI CSCRF
```

## Milestone 7 — AI layer

**Goal:** make the platform feel intelligent without making the core un-auditable.

Deliverables:

```text
natural language query
risk-driver explanations
recommendation explanations
optional anomaly/trend detection
```

## Milestone 8 — polish and proof

Deliverables:

```text
optimizer-vs-baseline benchmark
reproducible seeded simulation
data-confidence view
2-minute video
5-slide technical deck
architecture diagram
setup guide
```

---

# 38. Bottom line

SIH26105 is a large problem statement, but its size is deceptive. The hardest part is not building connectors to every security product; it is building a coherent bridge between **technical evidence, business context, quantitative uncertainty and investment decisions**.

The project becomes realistic when you make three architectural choices:

1. **Use public, real threat/vulnerability intelligence for the evidence layer.**
2. **Use a controlled synthetic organization to demonstrate telemetry and financial assumptions honestly.**
3. **Make the optimizer and scenario engine the technical centerpiece.**

The final product should feel less like:

```text
“AI cybersecurity dashboard”
```

and more like:

```text
Cyber Risk Decision Engine

        REAL EVIDENCE
              ↓
        RISK MODEL
              ↓
       FINANCIAL RANGE
              ↓
       WHAT-IF ENGINE
              ↓
        BUDGET SOLVER
              ↓
       SECURITY DECISION
```

That is a feasible implementation path that addresses the **entire SIH26105 problem statement** while giving you a demo a judge can understand in minutes.
