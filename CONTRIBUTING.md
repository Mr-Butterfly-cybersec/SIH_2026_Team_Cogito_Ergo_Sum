# Contributing

The full platform is in this repository. This document covers how to get it running locally, what
the conventions are, and how to submit a change.

---

## 1 · Get the code

```bash
git clone https://github.com/Mr-Butterfly-cybersec/SIH_2026_Team_Cogito_Ergo_Sum.git
cd SIH_2026_Team_Cogito_Ergo_Sum
make install      # uv sync + npm install
make test         # backend suite — you should see: 303 passed
```

If `make test` does not print **303 passed** on a clean clone, that is a bug in the repository, not
in your setup — please open an issue.

Run the stack (needs Docker and [uv](https://docs.astral.sh/uv/)):

```bash
make up           # db + api + web
#   API  http://localhost:8000/health
#   Docs http://localhost:8000/docs
#   Web  http://localhost:3000
make down         # stop
```

Local development without Docker for the app:

```bash
docker compose up -d db
make dev-api      # FastAPI on :8000, reloading
make dev-web      # Next.js on :3000
```

---

## 2 · Before you change something

Read these first — they explain why the code looks the way it does, which is usually the part that
surprises people:

| Read | Why |
|---|---|
| [`docs/architecture-decisions.md`](docs/architecture-decisions.md) | The decisions, their reasoning, and their costs. **Best first read.** |
| [`docs/architecture.md`](docs/architecture.md) | How the components fit together |
| [`docs/methodology.md`](docs/methodology.md) | The FAIR model and the formulas — the canonical reference |
| [`docs/TECHNICAL.md`](docs/TECHNICAL.md) | The end-to-end technical picture |

Then read the tests for the area you are touching. They encode the intended behaviour, including
several invariants that exist because they were once violated.

---

## 3 · Making a change

```bash
git checkout -b feat/<short-description>
# ... edit ...
make test && make lint
git add <specific paths>
git commit -m "feat(<area>): ..."
git push -u origin HEAD
```

Then open a pull request. CI runs on every PR; a pull request is not finished until it is green.

**Branch names:** `feat/…`, `fix/…`, `docs/…`, `chore/…` — a short description after the slash.

### Commit messages

Short and specific, in the imperative:

```
feat(optimization): add cost-per-rupee tie-breaking to the density baseline
fix(ai): reject prose when the model returns no tool call
test(compliance): assert CIS maps to fewer requirements than NIST
docs(architecture): record why the API proxies at runtime, not via rewrites
```

Prefixes: `feat` · `fix` · `test` · `docs` · `refactor` · `chore`.

---

## 4 · What CI checks, so you can run it yourself

**Backend** — `uv sync --frozen` → `ruff check .` → `ruff format --check .` → `pytest`

```bash
make lint     # ruff check + format check
make fmt      # fix formatting and lint issues automatically
make test     # pytest
```

**Frontend** — `npm ci` → `npm run lint` → `npm run build`

```bash
cd frontend && npm run lint && npm run build
```

The backend suite is **fully offline** — mocked HTTP transports and committed fixtures. It needs no
API keys and no network, so a failure is always something you can reproduce locally.

---

## 5 · Things worth knowing before you write code

These are the traps this codebase has already fallen into. All are explained at length in
`docs/architecture-decisions.md`.

- **No number may originate in the language model.** It selects a read-only tool, the engine
  computes, and the model explains. A model that could write would make answers order-dependent.
- **Every simulation is seeded and reproducible.** Same inputs plus the same seed must produce
  identical numbers. If you add a source of randomness, thread the seed through it.
- **The optimiser is scored by re-simulation, never by its own objective.** Search on the
  surrogate, claim only from the simulation.
- **A bound that can be violated is not a bound.** If the optimiser ever appears to beat the
  brute-force optimum, the answer is invalid, not better — the benchmark asserts this.
- **`overflow: hidden` on a chart container clips ECharts tooltips**, and `window.resize` alone
  does not keep charts sized. Use the `ResizeObserver` in `Chart.tsx`.
- **The API is proxied by a runtime route handler**, not a `rewrites()` rule, because
  `next.config.ts` is evaluated at build time and would freeze the destination.
- **`backend/data/normalized/` is committed deliberately.** `VulnerabilityStore` reads it at
  runtime; without it every scenario compiles empty.
- **Tests must not measure simulation noise.** If a test asserts a difference smaller than the
  Monte Carlo standard error, it will fail at random. Derive the tolerance from the standard error,
  or test against a deterministic stub.

---

## 6 · Using git for the first time?

One thing that silently breaks attribution: git records **`user.email`**, not your GitHub login. If
you commit with an identity that is not verified on your GitHub account, the commit shows in the
history as an **unlinked stranger** even though you pushed it. Set your own identity before your
first commit:

```bash
git config --global user.name  "Your Name"
git config --global user.email "<your-username>@users.noreply.github.com"
```

The `*@users.noreply.github.com` address works for every account and needs no lookup. You can also
find your exact address under GitHub → **Settings → Emails**.

---

## 7 · Questions

Open an issue. If something in this document was ambiguous or wrong, **say so** — a contributor who
had to guess is a bug in the document, not in the contributor.
