# CIVIL-OS — Phase 1 Working Prototype
**Project Context Engine** — core schemas · ECP assembler · basic CPO


Runnable reference implementation of TSD-001 v0.1 (2026-08-31) Phase 1 scope,
with an automated pytest suite and an end-to-end demonstration.


## Requirements
- Python 3.9+ (3.10+ recommended), pydantic ≥ 2.5, pytest ≥ 7.4


## Quick start
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"


pytest            # full test suite (~80 tests)
python demo.py    # end-to-end demo: Al-Wadi flood-protection scenario
```


## Demo scenario (TSD-001 §3.3)
Flood protection for 10,000 people in Al-Wadi, Riyadh. The demo shows:
1. Project / need / site / requirement registration through the `mcp-project` server.
2. ECP assembly + the jurisdiction cascade (SA → SBC codes).
3. The §7.3 confidence gate **blocking** a task on a level-E groundwater assumption.
4. A documented waiver unblocking a non-safety-critical task (level-D sign-off remains).
5. A **safety-critical** task that refuses waivers (hard block, no exceptions).
6. A simulated site investigation upgrading evidence E → A, producing ECP v2.
7. Full UTO lifecycle: ready → in_progress → under_review → approved → completed.
8. The complete audit trail (execution log) and JSON persistence round-trip.


## Traceability
See `IMPLEMENTATION_NOTES.md` for the spec→code traceability matrix, design
decisions, documented deviations, and the Phase 2 roadmap.
