# CIVIL-OS Phase 1 — Implementation Notes


## 1. Scope
Phase 1 = the **Project Context Engine**: §4 core data model, §5 ECP + assembler
(assembly rules 1–5), §6 UTO + lifecycle state machine, §7 confidence &
evidence system with §7.3 gate rules, a basic §3.2 CPO, and an in-process
`mcp-project` server per §8.


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
4. **Freshness interpretation (§5.3 r.2).** Expired ECP validity → *blocking*
   (re-assembly required); evidence with an overdue `next_review` → *warning*.
5. **Waivers are task-scoped** and are **never accepted for safety-critical
   parameters** (§7.3 last row). `UTO.safety_critical` is a Phase-1 extension;
   the per-discipline/phase matrix also carries a default safety-critical flag.
6. **ECP section duplication is faithful to §5.2** (site_data duplicates
   soil/hydrology/asset content). Confidence accounting walks only the
   canonical top-level sections (`engine/evidence.py:ECP_EVIDENCE_SECTIONS`)
   so nothing is double-counted.
7. **State machine is spec-literal.** Review-optional tasks pass through
   `under_review → approved` automatically rather than shortcutting
   `in_progress → approved`.
8. **Versioning (§5.3 r.4)** is keyed by (project, task) and content-hash
   idempotent: identical content re-assembles to the same version; any content
   change bumps the version. Tasks reference the exact ECP version consumed.
9. **Hazard/risk level derivation** uses a deterministic 5×5 heuristic
   (`derive_risk_level`) when `risk_level` is not supplied.
10. **Persistence** is an in-memory registry with a JSON round-trip. Production
    swaps this for the §3.1 data layer (PostgreSQL / Neo4j / S3 / time-series).
11. **MCP layer** is an in-process stand-in: `MCPServer` mirrors the §8 contract
    (tools, resources, §8.3 specification shape) with shallow required-argument
    validation; Pydantic performs deep validation at the handler boundary.
    Production replaces dispatch with a real MCP transport.


## 3. Traceability matrix
| Spec | Code |
|---|---|
| §3.2 CPO | `cpo/orchestrator.py::CivilProjectOrchestrator` |
| §4.2.1–4.2.7 | `schemas/project.py`, `need.py`, `requirement.py`, `site.py`, `design.py`, `risk.py` |
| §5.2 ECP schema | `schemas/ecp.py::ECP` (14 sections + identity) |
| §5.3 r.1 completeness | `engine/requirements_matrix.py`, `engine/validator.py::check_completeness` |
| §5.3 r.2 freshness | `engine/validator.py::check_freshness` |
| §5.3 r.3 confidence gate | `engine/gates.py::confidence_gate` |
| §5.3 r.4 versioning | `engine/versioning.py` |
| §5.3 r.5 jurisdiction cascade | `engine/jurisdiction.py::JurisdictionResolver` |
| §6.2 UTO | `schemas/uto.py::UTO` |
| §6.3 state machine | `cpo/state_machine.py` |
| §7.1–7.2 | `schemas/base.py` (ConfidenceLevel, ParameterEvidence) |
| §7.3 gate rules incl. waivers | `engine/gates.py` |
| §8.2 mcp-project | `mcp/project_context.py` |
| §8.3 server spec template | `mcp/server.py::MCPServer.specification()` |


## 4. Known Phase-1 limitations
- `lag_days` on task dependencies is parsed but not enforced.
- Approval chain is effectively single-step per `approve_task` call (multi-step
  chains stay `under_review` until each step is approved).
- No EDT (§10), no workflow engine (§11), no deterministic calculation engines.
- Codes registry covers SA/US/GB/DE plus an international fallback.


## 5. Phase 2 roadmap
EDT decision traces (§10) · real MCP transports + mcp-standards full code base ·
deterministic calculation engines behind mcp-analysis (bearing capacity, slope
stability, hydraulics) · workflow engine (§11) · graph persistence (Neo4j) ·
ISO 19650 CDE exchange.
