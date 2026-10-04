# CIVIL-OS — Implementation Status

An honest account of what this repository does today. It replaces earlier
documents that described the project as "production ready" with "60+ tests
passing"; at the time those were written the suite collected 14 passing tests
and errored on 21 others, and the HTTP service could not be imported.

Verified on Python 3.14 with pydantic 2.13, `pytest -q` → **87 passed**, and
`ruff check` → clean.

## Working today

| Area | State |
|---|---|
| §4 core data model (Project, Need, Requirement, Site, Design, Risk) | Implemented, validated, round-trips through JSON |
| §5.2 ECP schema (14 sections + identity) | Implemented |
| §5.3 assembly rules r.1–r.5 | Implemented and covered by tests |
| §5.3 r.4 versioning | Content-hash, idempotent, scoped per orchestrator |
| §5.3 r.3 confidence summary | Tallied from real evidence records during assembly |
| §6.2 UTO / §6.3 lifecycle | ready → in_progress → under_review → approved → completed, plus `blocked` |
| §7.1–7.2 confidence & evidence | A–E scale, `ParameterEvidence`, §8.4 MCP label mapping |
| §7.3 gate + waivers | Level-E blocking, task-scoped waivers, safety-critical refusal |
| §3.2 CPO | Project/site/need/requirement/ECP/task orchestration, audit trail |
| §8.2 `mcp-project` server | 11 in-process tools + resources, exposed at `/api/v1/mcp/specification` |
| §24 REST API | 9 spec endpoints plus task lifecycle, audit, registry exchange |
| §24.3 / §25.1 error contract | Error envelope and taxonomy implemented and tested |
| Thread safety | Registry mutations under `RLock` |
| Demo | `python demo.py` runs the Al-Wadi scenario end to end |
| Web UI | `uvicorn app.api:app` serves a working single-page console |
| CI | GitHub Actions: lint, test on 3.10–3.12, demo smoke test, `pip-audit` |

## Sprint 1–4 story status (ROADMAP-001)

Done: **P1-S1-01** datetime round-trip · **P1-S1-02** SHA-256 content hashing
· **P1-S1-03** confidence summary · **P1-S1-04** thread-safe registry ·
**P1-S3-01/02** audit trail · **P1-S3-03** `reject_task`/`rework_task` ·
**P1-S3-04** `blocked` state · **P1-S4-04** `lag_days` enforcement.

Not done:

- **P1-S2-01/02/03** — `ProjectService` / `ECPService` / `TaskService` have not
  been split out of the CPO. The CPO remains a single coordinator.
- **P1-S2-04** — no event bus for state changes.
- **P1-S4-01/02** — MCP resources and prompt templates are stub-level; the
  resource registry exists and is tested, but no project-scoped resource URIs or
  prompt templates are registered.
- **P1-S4-03** — no stdio/HTTP MCP transport; `MCPServer` is in-process only.

## Known limitations

- Persistence is in-memory plus a JSON snapshot. There is no database, no
  migration path implemented, and no concurrency control across processes.
- No authentication or authorization. The §19 RBAC matrix is documented but not
  enforced; every endpoint is open.
- The codes registry covers SA, US, GB, DE and an international fallback — not
  the 20+ jurisdictions of P3-S14-01.
- The MCP layer validates required arguments shallowly; deep validation happens
  in the pydantic models at the handler boundary.
- Approval chains are enforced in the orchestrator but there is no separation of
  duties — the same actor can start, review and approve a task.
- No EDT (§10), workflow engine (§11), calculation engines, or BIM/IFC.
- `TSD-001_v0.1_Technical_Specification.md` is missing §4–§16, so several clause
  references in `IMPLEMENTATION_NOTES.md` cannot be checked against the spec.
- Storage for large registries is O(n) scans for project-scoped lookups; fine at
  Phase-1 scale, not at 10k projects (§27.3).

## Deliberate deviations

See `IMPLEMENTATION_NOTES.md` §2. The most consequential:

1. `create_project` accepts a flat location (`country`, `latitude`, …) as well as
   a `location` mapping, matching the §8.2 tool signature.
2. `ecp_ref` is optional so a task can exist before an ECP is bound; the gate
   reports a missing ECP as a blocking issue rather than a construction error.
3. The confidence gate also requires a bound ECP, and treats an unverified
   (level-E) count of zero as *no verified information* (average `E`) rather
   than as good confidence.
4. `GateResult` supports both attribute access and tuple unpacking so the HTTP
   API and the older programmatic callers share one result object.
