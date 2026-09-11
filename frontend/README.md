# Frontend — Next.js dashboard

The decision dashboard for the CRQ platform. One page, six panels, no routing.

For the project overview, setup, and API reference see the [root README](../README.md).
For **why** the frontend is built this way, see
[`docs/architecture-decisions.md` §7](../docs/architecture-decisions.md) — including two traps worth
knowing before you change anything:

- **The API is proxied by a runtime route handler**, not a `rewrites()` rule, because
  `next.config.ts` is evaluated at build time and would freeze the destination.
- **`overflow: hidden` on a chart container clips ECharts tooltips**, and `window.resize` alone is
  not enough to keep charts sized — `Chart.tsx` uses a `ResizeObserver`.

## Run it

```bash
npm install
npm run dev          # http://localhost:3000
```

The dev server proxies `/api/*` and `/health` to the backend, which must be running:

```bash
# from the repo root
make dev-api         # FastAPI on :8000
# or
make up              # the whole stack in Docker
```

Override the proxy target with `API_PROXY_TARGET` (defaults to `http://localhost:8000`).

## Checks

```bash
npm run lint         # eslint
npm run build        # production build — also type-checks
```

CI runs exactly these two.

## Structure

```
src/
├── app/
│   ├── layout.tsx                 metadata, viewport, theme colour
│   ├── page.tsx                   the six panels, composed
│   ├── globals.css                theme tokens + motion (reduced-motion safe)
│   ├── providers.tsx              TanStack Query provider
│   ├── api/[...path]/route.ts     runtime proxy to the FastAPI backend
│   └── health/[[...rest]]/route.ts
├── components/
│   ├── ui.tsx                     Card · Stat · Badge · Skeleton · ErrorState · ShareBar
│   ├── ExecutiveBriefing.tsx      the decision, before the evidence
│   ├── ScenarioExplorer.tsx       ranked rail + inline drill-down
│   ├── OptimizerPanel.tsx         budget slider; solves once on mount
│   ├── CompliancePanel.tsx        seven-framework coverage
│   ├── AskPanel.tsx               questions, with the tool calls shown
│   ├── DataConfidencePanel.tsx    evidence mix, assumptions, run fingerprint
│   ├── SectionNav.tsx             sticky nav, scroll-spy, hotkeys 1–6
│   ├── HealthBadge.tsx
│   └── charts/                    Chart · LossCharts · StrategyBars
├── lib/
│   ├── api.ts                     typed client for every endpoint
│   ├── format.ts                  Indian short scale (₹ Cr / ₹ L) and colour maps
│   └── useCountUp.ts              rAF count-up for headline figures
└── types/api.ts                   hand-written types mirroring the API responses
```

## Conventions

- **Every fetching panel handles four states** — loading, error (with the reason and a Retry
  button), empty, and success. A failed request must never look like a slow one.
- **Accessibility is not optional:** `focus-visible` rings on interactive elements,
  `aria-pressed` / `aria-current` / `role="alert"` / `aria-live`, and colour never carries meaning
  alone — bands are labelled, not just coloured.
- **Motion is decorative and yields.** Everything collapses under `prefers-reduced-motion`, and
  nothing that carries information depends on an animation running.
- **ECharts is driven directly**, not through `echarts-for-react` (it depends on APIs React 19
  removed). Type formatter parameters as `unknown` and cast inside.
