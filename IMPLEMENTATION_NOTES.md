# CIVIL-OS Phase 1 — Implementation Notes

## 1. Scope

Phase 1 = the **Project Context Engine**: §4 core data model, §5 ECP + assembler
(assembly rules 1–5), §6 UTO + lifecycle state machine, §7 confidence & evidence
system with §7.3 gate rules, a §3.2 CPO, an in-process `mcp-project` server
(§8), and — added in v0.2 — an HTTP service implementing the §24 API contract
with a web UI.

See `STATUS.md` for what is and is not implemented.

## 2. Design decisions & documented deviations

1. **Canonical confidence scale is A–E (§7.1).** The MCP-side labels of §8.4
   (`MEASURED`, `INTERPOLATED`, `CORRELATED`, `ASSUMED`, `ENGINEERING_JUDGMENT`)
   are mapped onto A–E via `MCP_CONFIDENCE_MAP` (`schemas/base.py`).
2. **PROJECT pragmatic extensions.** §5.2 requires budget / schedule / land /
   risk-tolerance context that §4.2.1 does not source. Optional fields
   (`location`, `budget_amount`, `target_completion`, `land_area_available_m2`,
   `risk_tolerance`) were added to PROJECT as the Phase-1 source of that context.
3. **Location is mandatory before assembly.** ECP assembly raises
   `AssemblyError` if the project has no location — the §5.3 jurisdiction
   cascade cannot start without it (no silent defaults).
4. **Freshness interpretation (§5.3 r.2).** Expired ECP validity is *blocking*
   (re-assembly required); evidence with an overdue `next_review` is a warning.
5. **Waivers are task-scoped** and are **never accepted for safety-critical
   parameters** (§7.3 last row). `UTO.safety_critical` is a Phase-1 extension.
6. **ECP section duplication is faithful to §5.2** (site_data duplicates
   soil/hydrology/asset content). Confidence accounting walks only the canonical
   top-level sections (`engine/evidence.py:ECP_EVIDENCE_SECTIONS`) and excludes
   `confidence_summary` itself, so nothing is double-counted or self-amplifying.
7. **State machine is spec-literal.** Review-optional tasks pass through
   `mark_under_review` and auto-approve rather than shortcutting
   `in_progress → approved`.
8. **Versioning (§5.3 r.4)** is keyed by (project, task) and content-hash
   idempotent. The hash covers engineering content only: `ecp_id`, `created_at`,
   `version`, `content_hash` and the whole `validity` block are excluded, because
   `valid_from`/`valid_until` are derived from wall-clock time and would make
   every re-assembly look like a change. Version state lives on the CPO
   (`ECPVersionManager` instance), never in a class-level global.
9. **Hazard/risk level derivation** uses a deterministic 5×5 heuristic
   (`derive_risk_level`) when `risk_level` is not supplied.
10. **Persistence** is an in-memory registry with a JSON round-trip, serialised
    in pydantic JSON mode so datetimes and enums survive import/export with their
    types intact. Production swaps this for the §3.1 data layer
    (PostgreSQL / Neo4j / S3 / time-series); no migration code exists yet.
11. **MCP layer** is an in-process stand-in: `MCPServer` mirrors the §8 contract
    with shallow required-argument validation; pydantic performs deep validation
    at the handler boundary. There is no real transport.
12. **Task prerequisites are enforced on start.** `start_task` runs the §7.3 gate
    and the dependency check first. A gated task is parked in `blocked` with its
    unblock conditions in the execution log and `GateBlocked` is raised; when a
    waiver later opens the gate the task is released back to `ready`.
13. **Audit snapshots must be explicit.** Callers that mutate the live registry
    object pass `before=` to `update_project`, otherwise the recorded "before"
    state would already contain the new values.
14. **The gate requires a bound ECP.** A task with no `ecp_ref` reports a
    blocking issue rather than passing silently.
15. **HTTP layer.** Routes are exposed under `/api/v1/...` and mirrored at
    `/api/...` for compatibility. State lives in one process-level registry so
    the UI and the orchestrator share it. CORS is opt-in via
    `CIVIL_OS_CORS_ORIGINS`; wildcards are dropped because §19.5 requires a
    whitelist.

## 3. Traceability matrix

Clause references in the `v0.1` spec document are given as section numbers. Note
that §4–§16 are absent from the file in this repository, so only the headings
below can be verified.

| Spec | Code |
|---|---|
| §3.2 CPO | `cpo/orchestrator.py::CivilProjectOrchestrator` |
| §4.2.1–4.2.7 | `schemas/project.py`, `need.py`, `requirement.py`, `site.py`, `design.py`, `risk.py` |
| §5.2 ECP schema | `schemas/ecp.py::ECP` (14 sections + identity) |
| §5.3 r.1 completeness | `engine/requirements_matrix.py`, `engine/validator.py::check_completeness` |
| §5.3 r.2 freshness | `engine/validator.py::check_freshness` |
| §5.3 r.3 confidence | `engine/evidence.py::EvidenceCounter`, `engine/gates.py::ConfidenceGate` |
| §5.3 r.4 versioning | `engine/versioning.py` |
| §5.3 r.5 jurisdiction cascade | `engine/jurisdiction.py::JurisdictionResolver` |
| §6.2 UTO | `schemas/uto.py::UTO` |
| §6.3 state machine | `cpo/state_machine.py` |
| §7.1–7.2 | `schemas/base.py` (ConfidenceLevel, ParameterEvidence) |
| §7.3 gate rules incl. waivers | `engine/gates.py` |
| §8.2 mcp-project | `mcp/project_context.py` |
| §8.3 server spec template | `mcp/server.py::MCPServer.specification()` |
| §14 audit layer | `cpo/registry.py::ProjectRegistry.record_audit`, `schemas/base.py::AuditEntry` |
| §19.5 API security (CORS) | `app/api.py` CORS block |
| §24.1 REST contract | `app/api.py` route decorators |
| §24.3 error response | `app/api.py::error_body` |
| §25.1 error taxonomy | `app/api.py::ERROR_STATUS` + exception handlers |

## 4. Known limitations

- Persistence is in-memory + JSON only; no database, no multi-process safety.
- No authentication, authorization or rate limiting — §19 is unimplemented.
- Approval chains are sequential but do not enforce separation of duties.
- Project-scoped registry lookups are O(n) scans.
- The codes registry covers SA/US/GB/DE plus an international fallback.
- No EDT (§10), workflow engine (§11), or deterministic calculation engines.
- `TSD-001_v0.1_Technical_Specification.md` is missing §4–§16.

## 5. Roadmap

Next up, in order: split `ProjectService` / `ECPService` / `TaskService` out of
the CPO (P1-S2-01/02/03) and add a state-change event bus (P1-S2-04); then MCP
resource URIs and prompt templates (P1-S4-01/02) and a real MCP transport
(P1-S4-03). Phase 2 then moves to site intelligence — GIS, climate and hazard
data — per `ROADMAP-001-v0.2_Sprint_Plan.md`.
