# Contributing

This repository is built by a six-person team. Each person owns one module and contributes it
by **drag-and-drop in the browser** — no git, no terminal, nothing to install on your side.

---

## 1 · Get the code

You will receive **`sih26105-team-cogito.zip`**. Unzip it somewhere sensible:

```bash
unzip sih26105-team-cogito.zip -d sih26105
cd sih26105
```

> **One folder, one copy.** Do not unzip a second copy inside the first — if you do, git sees a
> nested repository later and refuses to track it properly.

### Run it (optional, but recommended)

Reading the code is easier when you have seen it work. This needs Docker and
[uv](https://docs.astral.sh/uv/); if you would rather not install anything yet, skip to §2.

```bash
make install     # installs backend (uv) + frontend (npm) dependencies
make test        # backend test suite — you should see: 303 passed
make up          # starts db + api + web
#   API  http://localhost:8000/health
#   Docs http://localhost:8000/docs
#   Web  http://localhost:3000
make down        # stop when finished
```

If `make test` does not print **303 passed**, tell the team before doing anything else — it means
your copy is not the one that was distributed.

---

## 2 · Read your module first

You are about to put your name on this code, so understand it before you upload it. Start here:

| Read | Why |
|---|---|
| `docs/architecture-decisions.md` | Every design decision and gotcha, in one place |
| `docs/architecture.md` | How the components fit together |
| `docs/methodology.md` | The FAIR model and the formulas your module implements |
| `docs/TECHNICAL.md` | The end-to-end technical picture |

Then read your own module's source and its tests under `backend/tests/` or in `frontend/src/`.

**This is not a formality.** If a judge asks you to walk through your module, the answer has to
come from you.

---

## 3 · Your module

Six modules, partitioned so **no two people touch the same files**. Find your row:

| Owner | Module | Paths you own |
|---|---|---|
| repo owner | Risk core + API surface | `backend/app/risk/`, `backend/app/api/`, `backend/app/main.py` |
| 1 | Evidence ingestion | `backend/app/ingestion/`, `backend/app/jobs/` |
| 2 | Investment optimizer | `backend/app/optimization/` |
| 3 | Compliance & frameworks | `backend/app/compliance/` |
| 4 | AI / explanation layer | `backend/app/ai/` |
| 5 | Frontend dashboard | `frontend/src/` |

Shared files (`docs/`, `infra/`, `Makefile`, `docker-compose.yml`, root config) are maintained by
the repo owner — if you need a change there, open a pull request or ask.

---

## 4 · Upload your module

All of this happens on github.com. Log in with **your own account** — the commit is attributed to
whoever is signed in, which is the whole point.

1. Open the repository.
2. **Add file → Upload files**.
3. **Drag your module folder** into the drop zone.
   GitHub accepts a directory and preserves its structure, so `backend/app/optimization/` arrives
   with every file inside it.
4. At the bottom, choose **"Create a new branch for this commit and start a pull request"** and
   name the branch `feat/<module>` — for example `feat/optimization`.
5. **Propose changes** → **Open pull request**.

### Rules

- **Upload your own folder only.** Never another person's module — the paths are disjoint so that
  two uploads can never conflict.
- **Never upload `.venv/`, `node_modules/`, `.next/` or `backend/data/`.** They are deliberately
  not in the zip. If you drag a folder that contains them, remove those subfolders first — a
  single one is hundreds of megabytes and will either be rejected or permanently bloat the repo.
- **One branch, one pull request.** Five contributors means five clean, reviewable diffs.
- **A pull request is not finished until CI is green.** The workflow runs on every PR; if it fails,
  the failure is yours to look at first.

---

## 5 · Making changes after your module is merged

Once your module is in the repository, come back to the browser and edit files directly:

1. Navigate to the file → the **pencil** icon → make your change.
2. **Commit changes** → create a new branch → **Propose changes** → pull request.

Same rule as before: your own module, one branch, one PR.

---

## 6 · Commit messages

Short and specific, in the imperative:

```
feat(optimization): add cost-per-rupee tie-breaking to the density baseline
fix(ai): reject prose when the model returns no tool call
test(compliance): assert CIS maps to fewer requirements than NIST
docs(architecture): record why the API proxies at runtime, not via rewrites
```

Prefixes: `feat` · `fix` · `test` · `docs` · `refactor` · `chore`.

---

## 7 · What CI checks, so you can run it yourself

Every pull request runs:

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

The test suite is **fully offline** — mocked HTTP transports and committed fixtures. It needs no
API keys and no network, so a failure is always something you can reproduce locally.

---

## 8 · If you prefer using git

That is fine, but read this first — it is the one thing that silently breaks attribution.

Git records **`user.email`**, not your GitHub login. If you commit with an identity that is not
verified on your GitHub account, the commit appears in the history as an **unlinked stranger**
even though you pushed it. Set your own identity before your first commit:

```bash
git config --global user.name  "Your Name"
git config --global user.email "<your-username>@users.noreply.github.com"
```

The `*@users.noreply.github.com` address works for every account and needs no lookup. You can also
find your exact address under GitHub → **Settings → Emails**.

```bash
git clone https://github.com/Mr-Butterfly-cybersec/SIH_2026_Team_Cogito_Ergo_Sum.git
cd SIH_2026_Team_Cogito_Ergo_Sum
git checkout -b feat/<module>
git add <your module paths>
git commit -m "feat(<module>): ..."
git push -u origin HEAD
```

---

## 9 · Questions

Open an issue, or ask in the team channel. If something in this document was ambiguous or wrong,
**say so** — a contributor who had to guess is a bug in the document, not in the contributor.
