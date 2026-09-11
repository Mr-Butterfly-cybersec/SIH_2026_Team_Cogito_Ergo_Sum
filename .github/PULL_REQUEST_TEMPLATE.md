## What this changes

<!-- One or two sentences. Which module, and what behaviour is different now? -->

## Module

<!-- Tick the one you own. -->

- [ ] `backend/app/risk/`, `backend/app/api/` — risk core + API surface
- [ ] `backend/app/ingestion/`, `backend/app/jobs/` — evidence ingestion
- [ ] `backend/app/optimization/` — investment optimizer
- [ ] `backend/app/compliance/` — compliance & frameworks
- [ ] `backend/app/ai/` — AI / explanation layer
- [ ] `frontend/src/` — dashboard
- [ ] shared (docs, infra, CI) — needs owner review

## How I verified it

<!--
Not "it should work" — what you actually ran. Paste the command and the result.

    make test          → 303 passed
    make lint          → all checks passed
-->

## Checklist

- [ ] I only changed files in **my own module** (or flagged it above if not)
- [ ] No `.venv/`, `node_modules/`, `.next/` or `backend/data/` in this diff
- [ ] `make test` passes locally
- [ ] `make lint` passes locally
- [ ] No secrets, keys or real client data in this diff
- [ ] I can explain what this code does — it is not just copied in
- [ ] Docs updated if behaviour or a public contract changed

## Notes for the reviewer

<!-- Anything you are unsure about, or want a second opinion on. "I don't know" is a fine answer here. -->
