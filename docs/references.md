# References

Every source this project draws on, with what we actually take from it and whether it is
**used in code** or merely **informed the design**.

The distinction matters. A reference list that mixes "we cite this in a mapping file" with "this
shaped our thinking" is padding. Each entry below states which it is.

**Legend**
- **Used** — read programmatically at runtime, or transcribed into the compliance catalog
- **Design** — shaped an approach or decision, but no data is taken from it
- **Context** — background only (market positioning, worth knowing)

---

## 1. Problem statement

| Ref | Source | Use |
|---|---|---|
| SIH26105 | *AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform* — AICTE Cyber Security Cell, SIH 2026 | **Design** — the specification this implements |
| — | SIH problem-statement archive: https://sih2026.vuce.in/ps/SIH26105 | |
| — | Official SIH portal: https://sih.gov.in/sih2026PS | |

---

## 2. Vulnerability & threat intelligence — **used live**

These four are fetched at runtime. Endpoints, rate limits and licences are in
`docs/data-sources.md`.

| Ref | Source | What we take | Use |
|---|---|---|---|
| **NVD** | NIST National Vulnerability Database, CVE API 2.0 — https://nvd.nist.gov/ | CVE id, CVSS base score + vector + **version**, CWE, description, references | **Used** — `ingestion/nvd.py` |
| **CVSS** | FIRST Common Vulnerability Scoring System v4.0 — https://www.first.org/cvss/v4.0/ | The scoring scale and the **version precedence chain** (v4 → v3.1 → v3.0 → v2) | **Used** — `normalization/vulnerabilities.py` |
| **EPSS** | FIRST Exploit Prediction Scoring System — https://www.first.org/epss/ | Exploitation probability, 0–1, 30-day horizon. Daily CSV for bulk, API for lookup | **Used** — `ingestion/epss.py` |
| **KEV** | CISA Known Exploited Vulnerabilities Catalog (CC0 1.0) — https://www.cisa.gov/known-exploited-vulnerabilities-catalog | Confirmed-exploited flag, ransomware association, due date | **Used** — `ingestion/kev.py` |
| **ATT&CK** | MITRE ATT&CK Enterprise — https://attack.mitre.org/ | Enterprise techniques, STIX 2.1. Release **19.2 → 697 techniques** ingested | **Used** — `ingestion/mitre.py` |
| **CWE** | MITRE Common Weakness Enumeration — https://cwe.mitre.org/ | Weakness classification carried alongside CVEs | **Used** (via NVD) |

**The three-feed argument, sourced.** FIRST states plainly that CVSS Base measures *severity*,
not risk — Environmental and Threat metric groups exist precisely because local context changes
the answer. EPSS likewise documents that its probability is not a complete risk score. Neither
claims to be sufficient. That is why the model takes all three plus business context.

---

## 3. Risk management & quantification — **design**

No data is fetched from these. They define the method.

| Ref | Source | What it shaped |
|---|---|---|
| **Open FAIR** | The Open Group Open FAIR Body of Knowledge, O-RA 2.0.1 / O-RT 3.0.1 — https://www.opengroup.org/open-fair | The factor decomposition: `LEF = TEF × Vulnerability`, derived Vulnerability, PLM/SLM/SLEF. The quantitative core |
| **NIST CSF 2.0** | https://www.nist.gov/cyberframework | The outcome taxonomy and reporting lens. **Not** the risk engine — used as the vocabulary for `SecurityFunction` and the crosswalk |
| **NIST SP 1347** | CSF 2.0 Informative References Quick-Start Guide — https://csrc.nist.gov/pubs/sp/1347/final | The machine-readable crosswalk ecosystem; validates the one-ontology approach |
| **NIST SP 800-30 Rev. 1** | Guide for Conducting Risk Assessments — https://csrc.nist.gov/pubs/sp/800/30/r1/final | The scenario object: threat source, vulnerable condition, likelihood, impact, existing controls, residual risk, treatment |
| **NISTIR 8286** | Integrating Cybersecurity and ERM — https://csrc.nist.gov/Pubs/ir/8286/Final | The cybersecurity risk register as the canonical internal object |
| **NISTIR 8286A Rev. 1** | Identifying and Estimating Cybersecurity Risk — https://www.nist.gov/publications/identifying-and-estimating-cybersecurity-risk-enterprise-risk-management-0 | Documented scenarios with explicit likelihood and impact distributions |
| **NISTIR 8286B** | Prioritizing Cybersecurity Risk — https://csrc.nist.gov/pubs/ir/8286/b/final | **The direct lineage of the optimizer**: prioritization incorporating projected cost of risk response |
| **NISTIR 8286C Rev. 1** | Staging Cybersecurity Risks for ERM — https://nvlpubs.nist.gov/nistpubs/ir/2025/NIST.IR.8286Cr1.pdf | Enterprise aggregation via PML/MFL and VaR-style reporting — why we report VaR and CVaR |
| **NIST SP 800-221** | Enterprise Impact of ICT Risk — https://csrc.nist.gov/pubs/sp/800/221/final | The `Asset → Service → BusinessUnit → Enterprise` aggregation hierarchy |
| **NIST SP 800-55 Vol. 1** | Measurement Guide for Information Security — https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=958991 | VaR definition and measurement discipline |
| **NISTIR 7385** | Analytical Approach to Cost-Effective, Risk-Based Budgeting — https://www.nist.gov/publications/analytical-approach-cost-effective-risk-based-budgeting-federal-information-system | The closest prior work to the investment problem itself |
| **OR-Tools CP-SAT** | Google OR-Tools constraint solver — https://developers.google.com/optimization/cp/cp_solver | The solver for the budget-constrained integer program |
| **Submodular maximization** | General result: budget-constrained submodular maximization is NP-hard | Why portfolios are **re-simulated rather than summed**, and why brute force is used to bound the gap |

---

## 4. Control & management-system frameworks — **used as mappings**

Transcribed by hand into `app/compliance/frameworks.py` and `catalog.py`. **No LLM-generated
mappings anywhere** — every reference is read from a published source and versioned, so a stale
mapping is visible rather than silently wrong.

| Framework | Version | Publisher | Referenced by | Requirements mapped |
|---|---|---|---|---|
| **NIST CSF 2.0** | 2.0 (2024-02-26) | NIST | category (`PR.AA`) | 38 |
| **CIS Controls** | v8.1 (2024-06-25) | Center for Internet Security | control number (`6.3`) | 21 |
| **ISO/IEC 27001** | 2022 Annex A | ISO/IEC | Annex A control (`A.8.5`) | 34 |
| **ISO/IEC 42001** | 2023 | ISO/IEC | Annex A group (`A.2`–`A.10`) | 10 |
| **RBI IT Governance** | 2023 | Reserve Bank of India | thematic area | 25 |
| **SEBI CSCRF** | 2024 | SEBI | cybersecurity function | 25 |
| **DPDP Act** | 2023 + 2025 Rules | MeitY, India | named statutory obligation | 13 |

Total: **38 canonical requirements, 7 frameworks.**

Sources: [NIST CSF](https://www.nist.gov/cyberframework) ·
[CIS v8.1](https://www.cisecurity.org/controls/v8-1) ·
[ISO 27001](https://www.iso.org/standard/27001) ·
[ISO 42001](https://www.iso.org/standard/42001) ·
[ISO 27005](https://www.iso.org/standard/80585) ·
[RBI](https://www.rbi.org.in/) · [SEBI](https://www.sebi.gov.in/) ·
[MeitY](https://www.meity.gov.in/)

---

## 5. India-specific regulatory material — **used**

| Ref | Source | What it shaped |
|---|---|---|
| **RBI Master Direction** on IT Governance, Risk, Controls and Assurance Practices (RBI/2023-24/107, 7 Nov 2023) | https://www.rbi.org.in/ | Governance, risk assessment, VA/PT, incident response, access control, audit trails, change/patch management. It explicitly ties cybersecurity budget to the threat landscape — a direct mandate for this platform |
| **SEBI CSCRF** (20 Aug 2024) | https://www.sebi.gov.in/legal/circulars/aug-2024/cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_85964.html | The six cybersecurity functions incl. Governance; a graded approach by entity type |
| **SEBI CSCRF clarifications** (31 Dec 2024) | https://www.sebi.gov.in/legal/circulars/dec-2024/clarifications-to-cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_90401.html | Versioned regulatory data — why the catalog carries a version |
| **SEBI CSCRF technical clarifications** (28 Aug 2025) | https://www.sebi.gov.in/legal/circulars/aug-2025/technical-clarifications-to-cybersecurity-and-cyber-resilience-framework-cscrf-for-sebi-regulated-entities-res-_96329.html | Current-state obligations |
| **DPDP Act, 2023** | https://www.indiacode.nic.in/ | The six `REQ-DPDP-*` obligations: notice/consent, data principal rights, breach notification, retention/purpose limitation, children's data, Significant Data Fiduciary duties |
| **DPDP Rules, 2025** | https://www.meity.gov.in/ | Operative detail and enforcement timeline; paired with the Act in the framework version string |
| **CERT-In Directions** (§70B, 28 Apr 2022) | https://www.cert-in.org.in/Directions70B.jsp | The six-hour incident-reporting obligation, noted on `REQ-INCIDENT-RESPONSE` |

**Why DPDP is modelled with its own requirements rather than as an alias for ISO 27001.** It is a
data-protection statute, not a security control set: notice, consent, data-principal rights and
children's data have no equivalent in ISO 27001's Annex A. Folding them in would have produced a
crosswalk that reports coverage for obligations nobody implemented. Most map to **organizational**
requirements, so they surface as gaps — which is the correct and useful answer.

**Why ISO 42001 is separate from ISO 27001.** AI management is genuinely new scope: impact
assessment, AI data governance, lifecycle verification, transparency and human oversight are not
in the cyber frameworks. The cyber frameworks above are *silent* on it, so AI requirements cite
`iso_42001` and no CIS reference — a test asserts this so the crosswalk cannot silently become a
copy.

---

## 6. Telemetry & integration — **design**

| Ref | Source | Use |
|---|---|---|
| **Wazuh** | Vulnerability detection — https://documentation.wazuh.com/current/user-manual/capabilities/vulnerability-detection/index.html | The realistic lab source an adapter targets (agent → inventory/alerts → normalization). Not a hard dependency: a CSV/replay adapter is the fallback so a missing agent cannot kill a demo |
| **Wazuh — how it works** | https://documentation.wazuh.com/current/user-manual/capabilities/vulnerability-detection/how-it-works.html | Feed-update behaviour, informing the ingestion cadence |

---

## 7. Commercial CRQ landscape — **context only**

Establishes that CRQ is a real product category rather than an invented hackathon concept — and
therefore that a "dashboard with a rupee number" is **not** sufficient differentiation. Vendor
claims are treated as marketing, not evidence. Nothing here is evaluated or benchmarked against.

| Vendor | Source | Note |
|---|---|---|
| **SAFE Security** | https://safe.security/ | Cyber risk quantification; ROSI calculator demonstrates risk-reduction-per-rupee as an established commercial use case |
| **C-Risk / SAFE One** | https://www.c-risk.com/crq-platform | FAIR-based financial quantification, control prioritization, ROI-based treatment |
| **CyberHQ (Avertro)** | https://www.avertro.com/solutions/use-cases/cyber-risk-quantification | Financial cyber risk with scenario/project modelling |
| **TRNEOPS** | https://trneops.com/ | Rupee-denominated CRQ positioning — relevant for an Indian market framing |

**Our differentiation, stated narrowly:** open-data-driven, transparent, reproducible
security-investment optimization with inspectable assumptions and a demonstrated
optimizer-vs-baseline result.

---

## 8. Software & libraries

| Component | Version | Licence | Role |
|---|---|---|---|
| Python | 3.12 | PSF | Runtime |
| FastAPI | ≥0.115 | MIT | API framework |
| Pydantic / pydantic-settings | ≥2.9 / ≥2.6 | MIT | Validation and configuration |
| SQLAlchemy | ≥2.0 (async) | MIT | ORM |
| asyncpg | ≥0.30 | Apache-2.0 | PostgreSQL driver |
| aiosqlite | ≥0.22 | MIT | SQLite driver for the offline test suite |
| Alembic | ≥1.14 | MIT | Migrations |
| httpx | ≥0.28 | BSD-3 | HTTP client for ingestion and tests |
| structlog | ≥24.4 | MIT/Apache-2.0 | Structured logging |
| NumPy | ≥2.1 | BSD-3 | Sampling, `Generator(PCG64)` |
| SciPy | ≥1.14 | BSD-3 | Percentiles and distribution support |
| OR-Tools | ≥9.11 | Apache-2.0 | CP-SAT solver |
| Hypothesis | ≥6.168 (dev) | MPL-2.0 | Property-based testing |
| pytest / pytest-asyncio / pytest-cov | ≥8.3 / ≥0.24 / ≥6.0 | MIT | Test suite |
| Ruff | ≥0.8 | MIT | Lint and format |
| Next.js | 16 | MIT | Frontend framework |
| React | 19 | MIT | UI |
| TypeScript | 5 | Apache-2.0 | Types |
| Tailwind CSS | v4 | MIT | Styling |
| Apache ECharts | — | Apache-2.0 | Charts |
| TanStack Query | — | MIT | Client data fetching |
| PostgreSQL | 16 | PostgreSQL Licence | Database |

---

## 9. Required attributions

These appear in the UI or `docs/data-sources.md`, as the licences require:

- "This product uses the NVD API but is not endorsed or certified by the NVD."
- CVSS is owned by FIRST and used by permission; scores are published with their vector string.
- "© 2026 The MITRE Corporation. This work is reproduced and distributed with the permission of
  The MITRE Corporation."
- CISA KEV data is released under **CC0 1.0**.
- MITRE ATT&CK is royalty-free **with attribution**.

---

## 10. Note on citation discipline

Two rules held throughout, and worth stating because they are easy to break:

1. **Regulatory references are transcribed, never generated.** An LLM asked for "the RBI clause
   covering patch management" will produce a plausible clause number. Every reference in
   `app/compliance/` was read from a published source, and where a source names a *thematic area*
   rather than a numbered clause (RBI, DPDP, SEBI), we cite the area — not an invented number.
2. **Absence of a source is stated, not filled.** Where a figure is an assumption rather than a
   citation, it is labelled `MODEL_ESTIMATE` or `SYNTHETIC_DEMO` and carries the reason. That is
   why the demo estate reports **LOW** evidence confidence: 64% of its inputs are synthetic, and
   the reference list above cannot change that.
