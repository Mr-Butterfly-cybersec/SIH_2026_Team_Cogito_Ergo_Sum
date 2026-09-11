## What this changes

<!-- One or two sentences. Which area, and what behaviour is different now? -->

## Area

<!-- Tick what this touches. -->

- [ ] `backend/app/risk/` — FAIR core (distributions, Monte Carlo, provenance)
- [ ] `backend/app/ingestion/` — evidence ingestion (NVD, EPSS, KEV, ATT&CK, CSV)
- [ ] `backend/app/optimization/` — investment optimizer and benchmark
- [ ] `backend/app/compliance/` — the ontology and framework crosswalk
- [ ] `backend/app/ai/` — tool layer, agent, providers, fallback
- [ ] `backend/app/api/` — routes and schemas
- [ ] `frontend/src/` — dashboard
- [ ] `docs/`, `infra/`, CI — shared

## How I verified it

<!--
Not "it should work" — what you actually ran. Paste the command and the result.

    make test          → 303 passed
    make lint          → all checks passed
-->

## Checklist

- [ ] `make test` passes locally
- [ ] `make lint` passes locally (and `npm run lint && npm run build` for frontend changes)
- [ ] No secrets, keys or real client data in this diff
- [ ] No generated junk committed (`.venv/`, `node_modules/`, `.next/`, `__pycache__/`, `backend/data/cache/`)
- [ ] Docs updated if behaviour or a public contract changed
- [ ] Any new randomness threads a seed through, so results stay reproducible
- [ ] No number is computed by the language model — it selects a tool and explains the result

## Notes for the reviewer

<!-- Anything you are unsure about, or want a second opinion on. "I don't know" is a fine answer here. -->
