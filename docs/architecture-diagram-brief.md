# System Architecture — Full Diagram Prompt (accurate)

Copy the block below into your image generator **together with your reference image**.
Every label is the real component from the implementation — do not let the model invent or
rename anything.

---

## PROMPT

> Use the attached image strictly as the **visual style reference** — match its layout,
> colour palette, typography, panel styling and spacing. Do not copy its text or subject.
>
> Produce a **large, detailed, professional system architecture diagram** for a cybersecurity
> risk quantification and investment optimization platform. Landscape 16:9, high resolution,
> print-quality, crisp at projector scale.
>
> **Layout:** a six-stage pipeline flowing **left to right**, then the outputs fanning downward
> at the right edge. Each stage is a labelled vertical column containing stacked component
> boxes. Thin arrows connect stages left to right. Keep strong alignment on a grid, generous
> white space, and readable text at every size.
>
> **Emphasis:** the **Analysis Engine** and **Decision Intelligence** columns are the
> differentiators — accent them with the reference's highlight treatment. All other columns
> stay neutral.
>
> Render exactly this content, spelled exactly as written. No invented components, no extra
> legends, no watermark, no diagram title.
>
> ---
>
> **① DATA INPUT**
> - NVD CVE API 2.0 · CVSS v4 → v3.1 → v3.0 → v2
> - FIRST EPSS · exploitation likelihood
> - CISA KEV · confirmed exploitation
> - MITRE ATT&CK · 697 techniques
> - Organisation telemetry · CSV / Wazuh
> - Asset & service inventory
>
> **② NORMALISATION**
> - Canonical assets · findings · controls
> - CVE → ATT&CK → scenario linking
> - CVSS version-aware severity bands
> - Asset criticality: availability · integrity · confidentiality · regulatory · internet exposure · dependency centrality
> - Control effectiveness from evidence
>
> **③ ANALYSIS ENGINE**
> - FAIR factor model
> - LEF = TEF × Vulnerability
> - Vulnerability = Pr(Threat Capability > Resistance Strength)
> - Beta-PERT three-point distributions
> - Monte Carlo · Poisson-thinning
> - Reproducible · seeded RNG
>
> **④ RISK OUTPUTS**
> - Expected Annual Loss (EAL)
> - P50 · P90 · P95 · P99
> - VaR · CVaR (tail risk)
> - Loss-exceedance curve
> - Provenance + confidence band on every figure
>
> **⑤ DECISION INTELLIGENCE**
> - Scenario engine · what-if
> - Control rollout · remediation delay · criticality change
> - CP-SAT budget optimizer
> - Budget · prerequisites · mandatory controls
> - Overlap-aware · submodular risk reduction
> - Every portfolio re-simulated
> - Baselines: CVSS-first · EPSS-first · risk-per-rupee · cheapest · exact optimum
>
> **⑥ INTERFACES**
> - REST API · FastAPI `/api/v1`
> - Dashboard · Next.js + ECharts
> - AI explanation layer · 6 read-only tools
> - Provider chain: Groq → Gemini → OpenRouter → Ollama
> - Framework mapping (7): NIST CSF 2.0 · CIS v8.1 · ISO 27001 · ISO 42001 · RBI · SEBI CSCRF · DPDP Act
>
> ---
>
> **A single callout box, joined to the Analysis Engine and Decision Intelligence columns:**
> `Every number is produced by the deterministic engine — the model calls it and explains.`
>
> **Style:** clean, corporate, technical documentation grade. Flat vector, precise alignment,
> sans-serif labels, one accent colour only. No 3D, no bevels, no drop shadows, no clip-art,
> no photorealism, no decorative icons.

---

## Accuracy notes (for you, not the generator)

- The tool count is **exactly six**; the AI layer is read-only and never writes.
- **Vulnerability is derived**, never an input — the classic FAIR mistake.
- Risk reduction is **submodular**; every portfolio is re-simulated rather than summed.
- Framework coverage is deliberately **not uniform** (CIS v8.1 is operational and omits
  governance/privacy/continuity).
- ATT&CK figure is enterprise release **19.2 → 697 techniques**, from a live ingest.

## If the generated text is garbled

Image models routinely misspell small caption text. Regenerate 2–3 times, and read every
label before it goes on the slide. If it stays wrong, build the six columns natively in
PowerPoint — the panel titles and body text above are the complete content list.
