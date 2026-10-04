# GitHub & CI Setup

The repository is published at <https://github.com/Happewton/civil-os-phase1>
and now ships a continuous-integration workflow at
`.github/workflows/ci.yml`. This file covers what the workflow does and the few
settings worth enabling in the GitHub UI.

> This guide previously claimed "60+ tests, all passing". That was never
> verified. The suite now runs 87 tests, all passing — see [`STATUS.md`](STATUS.md).

## What CI runs

| Job | Steps |
|---|---|
| `test` | `ruff check`, then `pytest -q`, then `python demo.py` as a smoke test, on Python 3.10 / 3.11 / 3.12 |
| `security` | `pip-audit --strict` over the resolved dependency set |

The demo smoke test matters: `demo.py` is the executable specification of the
Al-Wadi scenario, so CI fails if the end-to-end narrative breaks even when unit
tests still pass.

## Local reproduction

```bash
pip install -e ".[dev,web]"
ruff check civil_os app tests
pytest -q
python demo.py
```

## Recommended repository settings

- Default branch: `main`
- Require status checks: `test`, `security`
- Require branches to be up to date before merging
- Enable Dependabot for `pip` (the `pip-audit` job reports what it finds, but
  Dependabot proposes the upgrades)

## Releasing

```bash
pytest -q && python demo.py
git tag -a v0.2.0 -m "CIVIL-OS v0.2.0 — Project Context Engine + HTTP service"
git push origin v0.2.0
```

Tag notes should state what actually shipped. Do not copy the feature list from
`PROJECT_SUMMARY.md` or `DELIVERY_REPORT.md`; both are superseded pointers to
`STATUS.md`.

## Repository layout

```
civil_os/            core package (schemas, engine, cpo, mcp)
app/                 HTTP service and web UI
tests/               11 test modules, 87 tests
demo.py              end-to-end Al-Wadi scenario
.github/workflows/   CI
```
