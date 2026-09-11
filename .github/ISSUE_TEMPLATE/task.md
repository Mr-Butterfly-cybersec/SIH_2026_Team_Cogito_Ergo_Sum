---
name: Task
about: A piece of work assigned to one contributor and one module
title: "[<module>] "
labels: task
---

<!--
Assign exactly one person. Each task closes with a pull request, which is what puts a
contribution on the repository's front page.
-->

## Module

<!-- e.g. backend/app/optimization/ -->

## What to do

<!--
Be concrete. "Improve the optimizer" is not a task; "add a cost-per-rupee tie-break to the
density baseline and test it" is.
-->

## Definition of done

- [ ] Change implemented in the module named above
- [ ] Tests cover it (`make test` passes)
- [ ] `make lint` passes
- [ ] Pull request opened from a `feat/...` branch
- [ ] PR description explains **what** changed and **how it was verified**

## Useful reading first

<!-- Link the docs that explain this module. Start from docs/architecture-decisions.md. -->

- [ ] `docs/architecture-decisions.md`
- [ ] `docs/methodology.md`

## Notes

<!-- Constraints, gotchas, or a pointer to the relevant file. -->
