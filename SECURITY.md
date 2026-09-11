# Security policy

## Scope

This repository contains a **risk-modelling platform**, not a live security service. It ships no
credentials, no customer data, and no production endpoints.

The demonstration estate under `backend/app/seed/data/` is **fictional**. Its financial figures
are labelled `SYNTHETIC_DEMO` throughout and are not measured facts about any real organisation.

## Reporting a vulnerability

If you find a security issue in this code, please **do not open a public issue**. Report it
privately instead, using either:

- GitHub's **Report a vulnerability** button (Security → Advisories), or
- a direct message to the repository owner

Please include what you found, how to reproduce it, and the impact you believe it has. We will
acknowledge and investigate.

## Design decisions that affect security

Worth knowing before you assess the code:

- **No secrets are committed.** Configuration is read from environment variables; `.env.example`
  carries empty placeholders only. `.env` is gitignored.
- **The API is read-mostly by design.** Every analytical endpoint either reads the deterministic
  planning context or runs a seeded simulation. Nothing mutates stored state.
- **The AI layer has no write access.** Its six tools are read-only — enforced by a test asserting
  the engine is unchanged after invoking every tool. A model that could write would make answers
  order-dependent.
- **No number originates in the language model.** It selects a tool, the engine computes, and the
  model explains. The grounding check flags figures the tools did not return.
- **Input validation is at the boundary.** Malformed request bodies return 4xx, never 5xx — the
  property-based suite (`backend/tests/test_fuzz.py`) asserts this across pathological inputs.

## Known limitations

Stated openly rather than left to be discovered — see `docs/TECHNICAL.md` §15 for the full list:

- The grounding check is **heuristic and advisory**. It verifies that a figure is traceable to
  tool output, **not** that it was attributed to the correct subject.
- Absence from CISA KEV means "not yet confirmed exploited", not "safe".
- The demo API serves an in-memory planning context rather than Postgres.
