"""Regression tests for the ROADMAP-001 Sprint 1–4 hardening work.

Each test pins a defect that was present in the Phase-1 prototype so it cannot
silently return.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

import pytest

from civil_os import CivilProjectOrchestrator
from civil_os.cpo.registry import ProjectRegistry
from civil_os.engine import ECPVersionManager
from civil_os.engine.evidence import EvidenceCounter
from civil_os.schemas import (
    ConfidenceLevel,
    Hydrology,
    ParameterEvidence,
    Project,
    Site,
    SoilLayer,
    SoilProfile,
    TaskStatus,
)


# --------------------------------------------------------------------------- #
# P1-S1-01 — datetime round-trip fidelity
# --------------------------------------------------------------------------- #
def test_datetime_round_trip_is_exact(cpo, project, site, need):
    """Exported timestamps must re-import as the same instant, not a string."""
    cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)
    original = cpo.export_json()
    reimported = CivilProjectOrchestrator()
    reimported.import_json(original)

    before = cpo.get_project(project.project_id)
    after = reimported.get_project(project.project_id)
    assert after.created_at == before.created_at
    assert after.created_at.tzinfo is not None
    assert isinstance(after.created_at, datetime)


def test_execution_log_survives_round_trip(cpo, project):
    """Free-form log payloads keep their datetime type (P1-S1-01)."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Survey")
    cpo.start_task(task.uto_id, actor="Engineer")
    original_log_len = len(cpo.get_task(task.uto_id).execution_log)

    reimported = CivilProjectOrchestrator()
    reimported.import_json(cpo.export_json())

    entries = reimported.get_task(task.uto_id).execution_log
    assert len(entries) == original_log_len
    assert isinstance(entries[0].timestamp, datetime)


def test_export_uses_iso8601(cpo, project):
    """Timestamps serialise as ISO-8601, not Python's space-separated repr."""
    data = json.loads(cpo.export_json())
    assert "T" in data["projects"][0]["created_at"]


# --------------------------------------------------------------------------- #
# P1-S1-02 — content-hash idempotency, isolated version history
# --------------------------------------------------------------------------- #
def test_identical_content_keeps_the_same_version(cpo, project, site, need):
    first = cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)
    second = cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)
    assert first.content_hash == second.content_hash
    assert first.version == second.version == 1


def test_changed_content_bumps_the_version(cpo, project, site, need):
    first = cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)

    site.data_gaps = site.data_gaps + ["Newly identified gap"]
    cpo.update_site(site, reason="site investigation update")
    second = cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)

    assert second.content_hash != first.content_hash
    assert second.version == first.version + 1


def test_version_history_is_not_shared_between_orchestrators():
    """Each CPO keeps its own version history (no class-level global)."""
    a = CivilProjectOrchestrator()
    b = CivilProjectOrchestrator()
    pa = a.create_project(name="A", project_type="water", country="SA",
                          latitude=24.7, longitude=46.7)
    pb = b.create_project(name="B", project_type="water", country="SA",
                          latitude=24.7, longitude=46.7)
    assert a.assemble_ecp(pa.project_id).version == 1
    assert b.assemble_ecp(pb.project_id).version == 1
    assert a.version_manager is not b.version_manager


def test_hash_is_sha256_hex(cpo, project):
    ecp = cpo.assemble_ecp(project.project_id)
    assert len(ecp.content_hash) == 64
    int(ecp.content_hash, 16)  # valid hex


# --------------------------------------------------------------------------- #
# P1-S1-03 — confidence summary population
# --------------------------------------------------------------------------- #
def test_confidence_summary_counts_levels(cpo, project):
    """Soil layers at A/C/E and an E-level groundwater reading are tallied."""
    site = Site(
        project_id=project.project_id,
        soil_profiles=[SoilProfile(borehole_id="BH-1", layers=[
            SoilLayer(depth_from_m=0, depth_to_m=3, soil_type="fill",
                      confidence_level=ConfidenceLevel.A),
            SoilLayer(depth_from_m=3, depth_to_m=8, soil_type="clay",
                      confidence_level=ConfidenceLevel.C),
        ])],
        hydrology=Hydrology(groundwater_level=ParameterEvidence(
            parameter="groundwater_level", value=5.2, unit="m",
            source="assumption", confidence_level=ConfidenceLevel.E,
        )),
    )
    cpo.register_site(project.project_id, site)
    ecp = cpo.assemble_ecp(project.project_id, site_id=site.site_id)

    summary = ecp.confidence_summary
    assert summary.level_a_count >= 1
    assert summary.level_c_count >= 1
    assert summary.level_e_count >= 1
    assert summary.average_confidence in {"A", "B", "C", "D", "E"}


def test_confidence_summary_does_not_count_itself(cpo, project):
    """Re-assembling must not inflate the counts from its own previous output."""
    first = cpo.assemble_ecp(project.project_id)
    second = cpo.assemble_ecp(project.project_id)
    assert (first.confidence_summary.level_e_count
            == second.confidence_summary.level_e_count)


def test_evidence_counter_ignores_double_references(cpo, project):
    site = Site(project_id=project.project_id, soil_profiles=[SoilProfile(layers=[
        SoilLayer(depth_from_m=0, depth_to_m=3, soil_type="fill",
                  confidence_level=ConfidenceLevel.B),
    ])])
    cpo.register_site(project.project_id, site)
    ecp = cpo.assemble_ecp(project.project_id, site_id=site.site_id)
    counts = EvidenceCounter.count_by_level(ecp)
    assert counts[ConfidenceLevel.B] == 1


def test_uncertainty_items_reflect_open_gaps(cpo, project):
    site = Site(project_id=project.project_id,
                data_gaps=["Groundwater level unverified"])
    cpo.register_site(project.project_id, site)
    ecp = cpo.assemble_ecp(project.project_id, site_id=site.site_id)
    assert any("Groundwater level unverified" == u.parameter
               for u in ecp.confidence_summary.uncertainty_items)


# --------------------------------------------------------------------------- #
# P1-S1-04 — thread-safe registry
# --------------------------------------------------------------------------- #
def test_concurrent_registration_is_safe():
    registry = ProjectRegistry()
    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def register(i: int) -> None:
        try:
            barrier.wait(timeout=5)
            registry.register_project(Project(
                name=f"P{i}", project_type="water",
            ))
        except BaseException as exc:  # noqa: BLE001 - surfaced via the list
            errors.append(exc)

    threads = [threading.Thread(target=register, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors
    assert len(registry.list_projects()) == 8
    assert len({p.project_id for p in registry.list_projects()}) == 8


# --------------------------------------------------------------------------- #
# P1-S3-01/02 — audit trail
# --------------------------------------------------------------------------- #
def test_audit_trail_records_lifecycle(cpo, project):
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Survey")
    cpo.start_task(task.uto_id, actor="Engineer")

    entries = cpo.get_audit_log(task.uto_id)
    assert [e.action for e in entries] == ["registered"]

    execution = cpo.get_task(task.uto_id).execution_log
    assert [e.event_type for e in execution] == ["start_task"]
    assert execution[0].actor == "Engineer"


def test_audit_records_version_bump(cpo, project, site, need):
    cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)
    site.data_gaps = ["Another gap"]
    cpo.update_site(site, reason="new survey")
    ecp = cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)

    entries = cpo.get_audit_log(ecp.ecp_id)
    assert entries[-1].action == "assembled"
    assert entries[-1].after["version"] == 2


# --------------------------------------------------------------------------- #
# P1-S3-03/04 — rejection, rework, blocked state
# --------------------------------------------------------------------------- #
def test_reject_then_start_again(cpo, project):
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Design", requires_review=True)
    cpo.start_task(task.uto_id)
    cpo.mark_under_review(task.uto_id)

    cpo.reject_task(task.uto_id, actor="Checker", reason="Calculation error")
    assert cpo.get_task(task.uto_id).status == TaskStatus.READY
    cpo.start_task(task.uto_id)


def test_rework_returns_approved_task_to_in_progress(cpo, project):
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Design", requires_review=True)
    cpo.start_task(task.uto_id)
    cpo.mark_under_review(task.uto_id)
    cpo.approve_task(task.uto_id)

    cpo.rework_task(task.uto_id, actor="Checker", reason="Detail missing")
    assert cpo.get_task(task.uto_id).status == TaskStatus.IN_PROGRESS


def test_blocked_task_records_unblock_conditions(cpo, project):
    """A gated task parks in `blocked` and lists what would release it."""
    from civil_os.cpo.state_machine import GateBlocked
    from civil_os.schemas import AssumptionItem

    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Design", assumptions=[
        AssumptionItem(assumption_text="Groundwater at 5 m",
                       confidence_level=ConfidenceLevel.E),
    ])

    with pytest.raises(GateBlocked) as exc:
        cpo.start_task(task.uto_id)
    assert exc.value.issues

    stored = cpo.get_task(task.uto_id)
    assert stored.status == TaskStatus.BLOCKED
    entry = [e for e in stored.execution_log if e.event_type == "blocked"][-1]
    assert entry.details["issues"]


def test_blocked_task_is_released_once_the_waiver_clears_the_gate(cpo, project):
    """A blocked task must not become a dead end (regression: P1-S3-04)."""
    from civil_os.cpo.state_machine import GateBlocked
    from civil_os.schemas import AssumptionItem

    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Design", requires_review=True,
                           assumptions=[
        AssumptionItem(assumption_text="Groundwater at 5 m",
                       confidence_level=ConfidenceLevel.E),
    ])

    with pytest.raises(GateBlocked):
        cpo.start_task(task.uto_id)
    assert cpo.get_task(task.uto_id).status == TaskStatus.BLOCKED

    # Clearing the gate releases the task, and the lifecycle can continue.
    cpo.apply_waiver(
        task.uto_id,
        parameter="Groundwater at 5 m",
        rationale="Regional piezometer data supports 5 m with 90% confidence.",
        waived_by="Chief Engineer",
    )
    assert cpo.get_task(task.uto_id).status == TaskStatus.READY

    cpo.start_task(task.uto_id)
    cpo.mark_under_review(task.uto_id)
    cpo.approve_task(task.uto_id)
    cpo.complete_task(task.uto_id)
    assert cpo.get_task(task.uto_id).status == TaskStatus.COMPLETED

    events = [e.event_type for e in cpo.get_task(task.uto_id).execution_log]
    assert events.count("blocked") == 1
    assert "unblocked" in events


# --------------------------------------------------------------------------- #
# P1-S4-04 — dependency lag enforcement
# --------------------------------------------------------------------------- #
def test_dependency_must_complete_before_successor_starts(cpo, project):
    from civil_os.cpo.state_machine import StateMachineError
    from civil_os.schemas import TaskDependency

    ecp = cpo.assemble_ecp(project.project_id)
    upstream = cpo.create_task(project.project_id, ecp.ecp_id, "Survey", requires_review=True)
    downstream = cpo.create_task(project.project_id, ecp.ecp_id, "Design", dependencies=[
        TaskDependency(task_id=upstream.uto_id, task_name="Survey"),
    ])

    with pytest.raises(StateMachineError, match="Survey"):
        cpo.start_task(downstream.uto_id)

    cpo.start_task(upstream.uto_id)
    cpo.mark_under_review(upstream.uto_id)
    cpo.approve_task(upstream.uto_id)
    cpo.complete_task(upstream.uto_id)

    cpo.start_task(downstream.uto_id)
    assert cpo.get_task(downstream.uto_id).status == TaskStatus.IN_PROGRESS


def test_lag_days_defers_the_successor(cpo, project):
    from civil_os.cpo.state_machine import StateMachineError
    from civil_os.schemas import TaskDependency

    ecp = cpo.assemble_ecp(project.project_id)
    upstream = cpo.create_task(project.project_id, ecp.ecp_id, "Cure period",
                               requires_review=True)
    cpo.start_task(upstream.uto_id)
    cpo.mark_under_review(upstream.uto_id)
    cpo.approve_task(upstream.uto_id)
    cpo.complete_task(upstream.uto_id)

    downstream = cpo.create_task(project.project_id, ecp.ecp_id, "Load test", dependencies=[
        TaskDependency(task_id=upstream.uto_id, lag_days=7),
    ])

    with pytest.raises(StateMachineError, match="wait 7 day"):
        cpo.start_task(downstream.uto_id)

    cpo.get_task(upstream.uto_id).completed_at = datetime.now(timezone.utc) - timedelta(days=8)
    cpo.start_task(downstream.uto_id)


# --------------------------------------------------------------------------- #
# Gate result contract
# --------------------------------------------------------------------------- #
def test_gate_result_supports_attributes_and_unpacking(cpo, project):
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Design")

    result = cpo.check_gate(task.uto_id)
    can_proceed, issues = result  # tuple-style, as the demo and MCP layer use
    assert can_proceed is True
    assert issues == []
    assert result.can_proceed is True
    assert result.to_dict()["can_proceed"] is True


def test_gate_requires_a_bound_ecp(cpo, project):
    task = cpo.create_task(project.project_id, ecp_id=None, task_name="Design")
    result = cpo.check_gate(task.uto_id)
    assert result.can_proceed is False
    assert any("Engineering Context Packet" in i for i in result.issues)


def test_waiver_accepts_field_form(cpo, project):
    """The HTTP layer passes discrete fields rather than a Waiver object."""
    from civil_os.schemas import AssumptionItem

    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Design", assumptions=[
        AssumptionItem(assumption_text="Friction angle 35 deg",
                       confidence_level=ConfidenceLevel.E),
    ])
    cpo.apply_waiver(
        task.uto_id,
        parameter="Friction angle 35 deg",
        rationale="Correlated from regional SPT data at 90% confidence.",
        waived_by="Chief Engineer",
    )
    assert cpo.check_gate(task.uto_id).can_proceed is True


def test_multi_step_approval_chain(cpo, project):
    from civil_os.schemas import ApprovalStep

    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(project.project_id, ecp.ecp_id, "Design", requires_review=True,
                           approval_chain=[
        ApprovalStep(discipline="civil", approver_role="Discipline Engineer"),
        ApprovalStep(discipline="all", approver_role="Independent Checker"),
    ])
    cpo.start_task(task.uto_id)
    cpo.mark_under_review(task.uto_id)

    cpo.approve_task(task.uto_id, approver_name="Eng. A", approver_role="Discipline Engineer")
    assert cpo.get_task(task.uto_id).status == TaskStatus.UNDER_REVIEW

    cpo.approve_task(task.uto_id, approver_name="Eng. B", approver_role="Independent Checker")
    assert cpo.get_task(task.uto_id).status == TaskStatus.APPROVED


# --------------------------------------------------------------------------- #
# Version manager unit behaviour
# --------------------------------------------------------------------------- #
def test_version_manager_scopes_by_project_and_task(cpo, project):
    """Versions are tracked per (project, task) and never leak across CPOs."""
    from civil_os.engine import ECPAssembler

    manager = ECPVersionManager()
    site_a = Site(project_id=project.project_id, data_gaps=["Gap A"])
    site_b = Site(project_id=project.project_id, data_gaps=["Gap A", "Gap B"])

    ecp_1 = ECPAssembler.assemble(project=project, site=site_a, version_manager=manager)
    ecp_1_again = ECPAssembler.assemble(project=project, site=site_a, version_manager=manager)
    ecp_2 = ECPAssembler.assemble(project=project, site=site_b, version_manager=manager)

    assert manager.register_version(ecp_1, "p1", "t1") == 1
    assert manager.register_version(ecp_1_again, "p1", "t1") == 1
    assert manager.register_version(ecp_1, "p1", "t2") == 1
    assert manager.register_version(ecp_2, "p1", "t1") == 2
    assert manager.get_version("p1", "t1") == 2
    assert manager.get_version("p1", "t2") == 1
    assert manager.get_version("unknown", "t1") == 0
