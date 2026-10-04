# CIVIL-OS — Project Context Engine

A traceable engineering context layer for civil projects: every design input
carries provenance and a confidence level, and the §7.3 gate stops work from
proceeding on unverified assumptions.

Phase 1 scope (TSD-001 §4–§8): core data model, the Engineering Context Packet
(ECP) assembler, the Civil Project Orchestrator (CPO), the UTO lifecycle state
machine, the confidence/evidence system, an in-process `mcp-project` server and
an HTTP service with a web UI.

## Requirements

- Python 3.9+ (3.10+ recommended)
- `pydantic >= 2.5`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,web]"

pytest                             # 87 tests
python demo.py                     # end-to-end Al-Wadi scenario
uvicorn app.api:app --reload       # http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000> for the web UI. It creates a project, registers a
site and need, assembles an ECP, creates tasks, runs them through the confidence
gate and waiver flow, and shows the audit trail.

Disable the demo seed with `CIVIL_OS_SEED=0`. Configure CORS with
`CIVIL_OS_CORS_ORIGINS=https://example.com` (wildcards are ignored — §19.5
requires a whitelist).

## Library use

```python
from civil_os import CivilProjectOrchestrator

cpo = CivilProjectOrchestrator()
project = cpo.create_project(
    name="Al-Wadi Flood Protection",
    project_type="water",
    country="SA", latitude=24.7136, longitude=46.6753,
    region="Riyadh Province", municipality="Al-Wadi",
    budget_amount=15_000_000, risk_tolerance="conservative",
)
ecp = cpo.assemble_ecp(project.project_id)
task = cpo.create_task(project.project_id, ecp.ecp_id,
                       "Hydraulic analysis", discipline="civil")
gate = cpo.check_gate(task.uto_id)      # gate.can_proceed, gate.issues
```

## What the engine guarantees

| Rule | Behaviour |
|---|---|
| §5.3 r.1 completeness | Assembly fails if a critical section is empty |
| §5.3 r.2 freshness | Expired ECP validity is a blocking `ValidationError` |
| §5.3 r.3 confidence | `confidence_summary` is tallied from real evidence records |
| §5.3 r.4 versioning | Content-hash versioning; identical content ⇒ identical version |
| §5.3 r.5 jurisdiction | Location ⇒ country ⇒ applicable codes; no silent defaults |
| §7.3 gate | Level-E assumptions block; waivers are task-scoped |
| §7.3 safety | Safety-critical tasks refuse waivers outright |

A task also refuses to start while a `blocks`/`requires` dependency is
unfinished, and honours `lag_days` on that dependency.

## Project layout

```
civil_os/
  schemas/     §4 data model, §5.2 ECP, §6 UTO, §7 confidence & evidence
  engine/      ECP assembly, validation, versioning, gates, jurisdiction
  cpo/         orchestrator, registry (+ audit trail), state machine
  mcp/         in-process MCP server and the mcp-project tool set
app/
  api.py       §24 REST contract, §24.3 error envelope, §25.1 error taxonomy
  static/      single-page web UI
tests/         87 tests
```

## Documentation

| File | Contents |
|---|---|
| `IMPLEMENTATION_NOTES.md` | Design decisions, deviations, traceability, limitations |
| `ROADMAP-001-v0.2_Sprint_Plan.md` | Backlog of stories, with the ones already done marked |
| `TSD-001_v0.2_Missing_Sections.md` | §19–§27: security, deployment, CI/CD, API contract, errors, observability |
| `STATUS.md` | What is implemented today, and what is not |

`TSD-001_v0.1_Technical_Specification.md` contains only §1–§3 and §17; sections
§4–§16 were never filled in, so clause references in the traceability matrix
point at text that does not exist in this repository.

## License

Internal — development.
