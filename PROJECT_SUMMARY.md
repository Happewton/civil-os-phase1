# Project summary — superseded

This file previously described the repository as ready to push to GitHub with
"44 files, ~4,500 lines, 60+ tests all passing" and provided three options for
publishing it. Those numbers were not verified and the suite did not pass.

It has been replaced with a pointer. See:

- [`README.md`](README.md) — what the project is and how to run it
- [`STATUS.md`](STATUS.md) — verified implementation status and limitations
- [`IMPLEMENTATION_NOTES.md`](IMPLEMENTATION_NOTES.md) — design decisions,
  deviations and spec traceability

A continuous-integration workflow now runs on every push
(`.github/workflows/ci.yml`): lint, tests on Python 3.10–3.12, a demo smoke test
and a dependency vulnerability scan. The repository is already published at
<https://github.com/Happewton/civil-os-phase1>; this file no longer needs to
explain how to create it.
