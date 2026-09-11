# UI & UX

The dashboard is the part judges actually see. This document covers what it shows, why it is
arranged that way, and what was deliberately left out.

---

## 1. Design position

**One page, six panels, no navigation.** You scroll top to bottom and that is the entire
product.

This was a deliberate reversal. The first design had separate screens per concern — a scenario
page, an optimizer page, a compliance page. It was rejected because a judge evaluating the
system has to *hold the whole argument in their head at once*: exposure, then decision, then
compliance, then trust in the numbers. Splitting that across routes forces them to remember
what they saw two pages ago.

So: **linear narrative, inline drill-down, nothing hidden behind a click.** Selecting a scenario
opens it in place rather than navigating away, because the side-by-side comparison against the
scenario list *is* the insight.

**Visual language:** dark "control room" aesthetic — deep background with a subtle radial
gradient, frosted-glass panels, a single emerald→cyan accent reserved for the system's own
recommendation, and monospace for figures so numbers align and read as data. Colour is
meaningful, not decorative: rose/orange/yellow/green encode criticality bands, and the accent
gradient appears **only** on the optimizer's own proposal so the eye lands there.

---

## 2. Reading order and why

| # | Panel | Question it answers |
|---|---|---|
| 1 | **Header + health** | Is it live, and what is this? |
| 2 | **Posture strip** | How much are we exposed to, and how much should we trust it? |
| 3 | **Scenario explorer** | Where does that exposure come from? |
| 4 | **Investment optimizer** | What should we do about it? |
| 5 | **Framework alignment** | Does that satisfy our regulators? |
| 6 | **Ask the engine** | Can I interrogate it in my own words? |
| 7 | **Data confidence & assumptions** | Why should I believe any of this? |

The sequence is a **decision funnel**: exposure → its causes → the action → the compliance
consequence → interrogation → trust. Panels 6 and 7 are the honesty layer, positioned last
because that is where a sceptic arrives after reading the headline number.

A **section jump-nav** sits under the header — six anchor pills. It does not navigate away; it
scrolls. Long single-page layouts need landmarks or people lose their place.

---

## 3. Panel detail

### Header + HealthBadge
Project identity, the one-line thesis — *"From CVE to ₹ impact to optimal security spend"* — and
a live API indicator that polls every 15s. The status dot is tri-state (connecting / online /
offline) rather than binary, so "not yet loaded" never masquerades as "broken".

### Posture strip
The four figures a CISO asks for first: **Expected Annual Loss**, **P90** (1-in-10 year),
**P95 / VaR** (1-in-20 year), and the **evidence confidence band**. Below: criticality mix as
coloured badges (16 CRITICAL / 11 HIGH / 6 MEDIUM) and estate counts (33 assets, 24 findings,
11 controls, 18 CVEs enriched).

Showing confidence *next to* the headline number is the most important layout decision on the
page. A rupee figure without its confidence band invites false precision.

### Scenario explorer
Two columns: a ranked scenario list (exposure share bars, listed by current-posture EAL) and a
detail pane that opens in place. For the selected scenario:

- **Identity row** — name, ID, asset, category, plus CVSS / EPSS / confidence badges
- **Six statistics** — EAL, P90, P95, CVaR 95, Vulnerability, Loss Event Frequency
- **Two charts** — loss-exceedance curve (`P(annual loss > x)`) and the simulated annual-loss
  histogram, both annotated with P90/P95 markers
- **What-if controls** — toggle candidate controls and watch EAL move; a green banner shows
  `before → after` and the rupee reduction

Below that, two independent stress tests: **Cost of delay** (postpone remediation N days) and
**Criticality stress test** (re-materialize the asset as business-critical).

**Trial-count control** — Fast 5k / Balanced 20k / Precise 60k. Exposing this is unusual and
intentional: it teaches the user that tail estimates get tighter with more samples, which is a
real property of the model rather than a loading spinner.

### Investment optimizer
A **budget slider (₹5L → ₹1 Cr)** and one *Optimize spend* button. Returns five statistics (risk
removed, EAL after, spend, risk-per-rupee, ROSI-like), the recommended portfolio as chips
showing each control's standalone reduction and the FAIR factor it moves, and a **cyan callout**
comparing against CVSS-first in percentage points.

Then the evidence: a bar chart of every strategy's re-simulated risk reduction (optimizer
gradient-highlighted, baselines grey) beside a table of the same numbers. The point is that all
strategies were scored on the **same harness** — the comparison is visible, not asserted.

### Framework alignment
Coverage across NIST CSF 2.0 / CIS v8.1 / ISO 27001 / RBI / SEBI CSCRF, with covered / partial /
gap counts and the **rupee exposure of the gaps**. Framework switcher is a simple selector —
seven frameworks on one axis, not seven screens.

### Ask the engine
A question box with five suggested questions (clickable, so the demo never stalls on "what do I
type?"). Each answer shows **the tool calls that produced it** (`get_top_risks()`, …) and
whether it came from an LLM or the deterministic path. History accumulates in-session, newest
first.

Surfacing the tool calls is the whole point. It converts the AI from a black box into something
the viewer can audit on screen — they can see the number came from the engine, not the model.

### Data confidence & assumptions
The panel that closes the honesty loop: a stacked bar of where every parameter came from (public
data / telemetry / user input / model estimate / **synthetic demo**), a legend with counts, the
assumptions the result depends on, and the run fingerprint (`model v0.1.0 · 20,000 trials ·
seed 42`).

On the demo estate this reads **LOW · 25%**, because 64% of inputs are synthetic. That is the
correct and intended display. A dashboard claiming HIGH confidence on invented data would
discredit everything above it.

---

## 4. UX engineering decisions

**Every async surface has four states, not two.** Loading (shaped skeletons matching the final
layout, so nothing jumps), error (with the failure reason *and* a **Retry** button),
empty (deliberate styled message, so zero results don't look broken), and success. A failed
request must never be indistinguishable from a slow one — the previous version could spin
forever on a dead API, which is the single worst failure mode in a live demo.

**Accessibility is built in, not retrofitted:**
- `focus-visible` rings on every interactive element (keyboard navigation is visible)
- `aria-pressed` on toggles, `aria-current` on the active scenario, `role="alert"` on errors,
  `aria-live="polite"` on the Ask history and loading indicators
- `role="group"` + label on the segmented control
- Colour never carries meaning alone — bands are labelled ("CRITICAL"), not just coloured

**Truncation was a measured defect.** Screenshot review found scenario titles cut mid-word
("Third-party service provider co…"). Fixed with two-line clamping and a scrollable list, so
long real-world scenario names stay readable.

**Sticky scenario list** on large screens — the detail pane is long, and losing the scenario list
while scrolling breaks the comparison.

**Loading skeletons match final geometry**, which is what separates a considered interface from
a jittery one: content does not shift when it arrives.

---

## 5. Technical notes

- **Next.js 16 + React 19 + Tailwind v4**, TypeScript strict.
- **ECharts driven directly**, not `echarts-for-react` — the wrapper lags React 19 support, so
  charts are bound manually with a typed formatter (a real typing problem under strict TS).
- **TanStack Query** for fetching/caching/mutations; queries are keyed on
  `[simulate, scenarioId, selectionKey, trials]` so re-simulation happens exactly when an input
  changes, and not otherwise.
- **Server-side API proxy** (`src/app/api/[...path]/route.ts`) instead of exposing the API
  directly. This replaced a build-time `NEXT_PUBLIC_API_BASE_URL`, which was a genuine bug:
  `NEXT_PUBLIC_*` is inlined when the bundle is built, so a runtime value set by Docker Compose
  was **silently ignored** and the app still pointed at `localhost:8000`. Proxying through a
  route handler reads the environment per request, so **one image works on localhost, behind a
  tunnel, or deployed** — and because the browser only ever talks to one origin, there is no
  CORS surface at all.
- **Money in Indian short scale** (₹ Cr / ₹ L) via a shared formatter — matching how Indian
  stakeholders actually read amounts.
- **Single-page, six panels** — no routing, so there is no "which page was that on?".

---

## 6. What was deliberately left out

- **No login or user management.** It adds nothing to a risk-modelling demonstration and would
  cost most of a presentation slot.
- **No separate scenario/optimizer/compliance routes.** Rejected in favour of the single page.
- **No live-editable scenario parameters.** Modelling inputs are fixed for reproducibility; the
  what-if controls change *selection*, not the underlying distributions, so every number stays
  traceable to a seeded run.
- **No animated chart transitions beyond ECharts defaults.** Motion for its own sake slows
  comprehension; the aesthetic is carried by colour and layout.

---

## 7. Verification

Dashboard rendered and reviewed in a real browser (headless Chromium, full-page capture at
1280px). Confirmed live: posture strip populated, scenario drill-down with both charts drawn
and P90/P95 markers, optimizer returning a 6-control portfolio at ₹25L with the CVSS-first
comparison, compliance coverage across seven frameworks, and the Ask panel answering from the
deterministic path.

`npm run lint` and `npm run build` both clean; all six panels verified against the live API.
