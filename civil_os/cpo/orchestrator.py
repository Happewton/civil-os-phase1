"""TSD-001 §3.2 — Civil Project Orchestrator (CPO)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ..engine import AssemblyError, ConfidenceGate, ECPAssembler, ECPVersionManager
from ..engine.gates import GateResult
from ..schemas import ECP, UTO, Need, Project, Requirement, Site, TaskStatus, Waiver
from .registry import ProjectRegistry
from .state_machine import GateBlocked, StateMachineError, UTOStateMachine


class CivilProjectOrchestrator:
    """§3.2 — main orchestrator for CIVIL-OS project workflow.

    Coordinates:
    - Project / site / need / requirement registration
    - ECP assembly and versioning
    - Task lifecycle and state management
    - Confidence gating and waivers
    """

    def __init__(
        self,
        registry: Optional[ProjectRegistry] = None,
        version_manager: Optional[ECPVersionManager] = None,
    ) -> None:
        #: Shared so the HTTP layer and the orchestrator see the same data.
        self.registry = registry if registry is not None else ProjectRegistry()
        #: Per-orchestrator ECP version history (no cross-project leakage).
        self.version_manager = version_manager if version_manager is not None else ECPVersionManager()

    # ------------------------------------------------------------------ #
    # Project management
    # ------------------------------------------------------------------ #
    def create_project(
        self,
        name: str,
        project_type: str,
        location: Optional[dict] = None,
        *,
        country: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        region: str = "",
        municipality: str = "",
        elevation_m: float = 0.0,
        **kwargs: Any,
    ) -> Project:
        """Create and register a new project.

        Accepts the location either as a ``location={...}`` mapping or as flat
        ``country`` / ``latitude`` / ``longitude`` / ``region`` / ``municipality``
        keywords. The flat form matches the §8.2 ``create_project`` MCP tool and
        the HTTP API; the mapping form is kept for programmatic callers.
        """
        from ..schemas import Location, ProjectType

        if location is not None:
            loc = Location(**location)
        else:
            missing = [f for f, v in (("country", country), ("latitude", latitude),
                                      ("longitude", longitude)) if v is None]
            if missing:
                raise AssemblyError(
                    "create_project requires a location: pass location={...} or "
                    f"the flat fields {', '.join(missing)}"
                )
            loc = Location(
                country=country,
                latitude=latitude,
                longitude=longitude,
                region=region,
                municipality=municipality,
                elevation_m=elevation_m,
            )

        try:
            ptype = ProjectType(project_type)
        except ValueError as exc:
            raise AssemblyError(
                f"Unknown project_type {project_type!r}; expected one of "
                f"{', '.join(t.value for t in ProjectType)}"
            ) from exc

        # Guard against kwargs smuggling a second location definition.
        kwargs.pop("location", None)
        project = Project(name=name, project_type=ptype, location=loc, **kwargs)
        self.registry.register_project(project)
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve a project."""
        return self.registry.get_project(project_id)

    def update_project(
        self,
        project: Project,
        actor: str = "system",
        reason: str = "",
        before: Optional[dict] = None,
    ) -> Project:
        """Persist changes to a project and record them in the audit trail.

        Pass ``before`` (a pre-mutation snapshot) when the caller edited the
        live registry object, otherwise the recorded "before" would already
        contain the new values.
        """
        self.registry.update_project(project, actor=actor, reason=reason, before=before)
        return project

    def list_projects(self) -> list[Project]:
        """List all projects."""
        return self.registry.list_projects()

    # ------------------------------------------------------------------ #
    # Site management
    # ------------------------------------------------------------------ #
    def register_site(self, project_id: str, site: Site) -> str:
        """Register a site for a project."""
        site.project_id = project_id
        return self.registry.register_site(site)

    def update_site(self, site: Site, actor: str = "system", reason: str = "") -> Site:
        """Persist site changes and record them in the audit trail."""
        self.registry.update_site(site, actor=actor, reason=reason)
        return site

    def get_sites_for_project(self, project_id: str) -> list[Site]:
        """List sites for a project."""
        return self.registry.get_sites_for_project(project_id)

    # ------------------------------------------------------------------ #
    # Need management
    # ------------------------------------------------------------------ #
    def register_need(self, project_id: str, need: Need) -> str:
        """Register a need for a project."""
        need.project_id = project_id
        return self.registry.register_need(need)

    def get_needs_for_project(self, project_id: str) -> list[Need]:
        """List needs for a project."""
        return self.registry.get_needs_for_project(project_id)

    # ------------------------------------------------------------------ #
    # Requirement management
    # ------------------------------------------------------------------ #
    def register_requirement(self, project_id: str, requirement: Requirement) -> str:
        """Register a requirement for a project."""
        requirement.project_id = project_id
        return self.registry.register_requirement(requirement)

    def get_requirements_for_project(self, project_id: str) -> list[Requirement]:
        """List requirements for a project."""
        return self.registry.get_requirements_for_project(project_id)

    # ------------------------------------------------------------------ #
    # ECP assembly
    # ------------------------------------------------------------------ #
    def assemble_ecp(
        self,
        project_id: str,
        site_id: Optional[str] = None,
        need_id: Optional[str] = None,
        validity_days: int = 30,
    ) -> ECP:
        """Assemble an ECP for a project (§5).

        Applies assembly rules: completeness, freshness, confidence, versioning
        and the jurisdiction cascade.
        """
        project = self.get_project(project_id)
        if not project:
            raise AssemblyError(f"Project {project_id} not found")

        site = self.registry.get_site(site_id) if site_id else None
        need = self.registry.get_need(need_id) if need_id else None

        ecp = ECPAssembler.assemble(
            project=project,
            site=site,
            need=need,
            validity_days=validity_days,
            version_manager=self.version_manager,
        )

        self.registry.register_ecp(ecp)
        self.registry.record_audit(
            "ecp", ecp.ecp_id, "assembled",
            after={"version": ecp.version, "content_hash": ecp.content_hash},
        )
        return ecp

    def get_ecp(self, ecp_id: str) -> Optional[ECP]:
        """Retrieve an ECP by ID."""
        return self.registry.get_ecp(ecp_id)

    def get_ecps_for_project(self, project_id: str) -> list[ECP]:
        """List ECPs for a project."""
        return self.registry.get_ecps_for_project(project_id)

    # ------------------------------------------------------------------ #
    # Task management
    # ------------------------------------------------------------------ #
    def create_task(
        self,
        project_id: str,
        ecp_id: Optional[str] = None,
        task_name: str = "",
        discipline: str = "civil",
        **kwargs: Any,
    ) -> UTO:
        """Create a new task (UTO) bound to a specific ECP version."""
        from ..schemas import ECPRef, TaskStatus

        project = self.get_project(project_id)
        if not project:
            raise AssemblyError(f"Project {project_id} not found")

        ecp_ref = None
        if ecp_id:
            ecp = self.registry.get_ecp(ecp_id)
            if not ecp:
                raise AssemblyError(f"ECP {ecp_id} not found")
            ecp_ref = ECPRef(ecp_id=ecp.ecp_id, version=ecp.version)

        task = UTO(
            project_id=project_id,
            ecp_ref=ecp_ref,
            task_name=task_name,
            discipline=discipline,
            status=TaskStatus.READY,
            **kwargs,
        )
        self.registry.register_task(task)
        return task

    def get_task(self, task_id: str) -> Optional[UTO]:
        """Retrieve a task."""
        return self.registry.get_task(task_id)

    def get_tasks_for_project(self, project_id: str) -> list[UTO]:
        """List tasks for a project."""
        return self.registry.get_tasks_for_project(project_id)

    # ------------------------------------------------------------------ #
    # Task lifecycle
    # ------------------------------------------------------------------ #
    def _require_task(self, task_id: str) -> UTO:
        task = self.get_task(task_id)
        if not task:
            raise StateMachineError(f"Task {task_id} not found")
        return task

    def start_task(self, task_id: str, actor: str = "system") -> UTO:
        """Start a task (ready → in_progress).

        Enforces §7.3 (confidence gate) and blocking dependencies first. When a
        prerequisite is unmet the task is parked in ``blocked`` with its unblock
        conditions recorded, and :class:`GateBlocked` is raised.
        """
        from ..schemas import TaskStatus

        task = self._require_task(task_id)

        result = self.check_gate(task_id)
        if not result.can_proceed:
            if task.status != TaskStatus.BLOCKED:
                task.status = TaskStatus.BLOCKED
                UTOStateMachine.log_event(
                    task, "blocked", actor,
                    "Confidence gate blocked task start",
                    details={"issues": result.issues},
                )
            raise GateBlocked(result.message, issues=result.issues)

        self._check_dependencies(task)

        UTOStateMachine.start_task(task, actor=actor)
        task.started_at = datetime.now(timezone.utc)
        return task

    def _check_dependencies(self, task: UTO) -> None:
        """Raise if a ``blocks``/``requires`` dependency is not yet satisfied.

        Honours ``lag_days``: a dependency that completed N days ago still
        blocks the dependent task until the lag has elapsed.
        """
        now = datetime.now(timezone.utc)
        for dep in task.dependencies:
            if dep.dependency_type not in ("blocks", "requires"):
                continue

            upstream = self.registry.get_task(dep.task_id)
            if upstream is None:
                raise StateMachineError(
                    f"Task {task.uto_id} depends on unknown task {dep.task_id}"
                )
            if upstream.status != "completed":
                raise StateMachineError(
                    f"Task {task.uto_id} is blocked by {dep.task_id} "
                    f"({dep.task_name or upstream.task_name}), which is "
                    f"'{upstream.status}' not 'completed'"
                )
            if dep.lag_days > 0:
                ready_at = (upstream.completed_at or now) + timedelta(days=dep.lag_days)
                if now < ready_at:
                    raise StateMachineError(
                        f"Task {task.uto_id} must wait {dep.lag_days} day(s) after "
                        f"{dep.task_id} completes; earliest start "
                        f"{ready_at.isoformat()}"
                    )

    def mark_under_review(self, task_id: str, actor: str = "system") -> UTO:
        """Mark a task for review (in_progress → under_review, else auto-approve)."""
        task = self._require_task(task_id)
        UTOStateMachine.mark_under_review(task, actor=actor)
        return task

    def approve_task(
        self,
        task_id: str,
        actor: str = "system",
        approver_name: Optional[str] = None,
        approver_role: Optional[str] = None,
        comments: str = "",
    ) -> UTO:
        """Approve a task (under_review → approved).

        When the task carries an approval chain, one call approves the next
        pending step; the task only reaches ``approved`` once every required
        step is signed off.
        """
        task = self._require_task(task_id)

        pending = next((s for s in task.approval_chain
                        if s.required and s.approved_by is None), None)
        if pending is not None:
            pending.approved_by = approver_name or actor
            pending.approved_at = datetime.now(timezone.utc)
            if comments:
                pending.comments = comments
            UTOStateMachine.log_event(
                task, "approval_step", approver_name or actor,
                f"Approval step '{pending.approver_role}' signed off",
                details={"discipline": pending.discipline,
                         "remaining_steps": sum(1 for s in task.approval_chain
                                                if s.required and s.approved_by is None)},
            )
            if any(s.required and s.approved_by is None for s in task.approval_chain):
                return task  # still under review

        UTOStateMachine.approve_task(task, actor=approver_name or actor)
        return task

    def reject_task(self, task_id: str, actor: str = "system", reason: str = "") -> UTO:
        """Reject work under review; the task returns to ``ready`` for rework."""
        task = self._require_task(task_id)
        UTOStateMachine.reject_task(task, actor=actor, reason=reason)
        return task

    def rework_task(self, task_id: str, actor: str = "system", reason: str = "") -> UTO:
        """Send an approved task back to ``in_progress`` for rework."""
        task = self._require_task(task_id)
        UTOStateMachine.rework_task(task, actor=actor, reason=reason)
        return task

    def complete_task(self, task_id: str, actor: str = "system") -> UTO:
        """Complete a task (approved → completed)."""
        task = self._require_task(task_id)
        UTOStateMachine.complete_task(task, actor=actor)
        task.completed_at = datetime.now(timezone.utc)
        return task

    # ------------------------------------------------------------------ #
    # Confidence gating & waivers
    # ------------------------------------------------------------------ #
    def check_gate(self, task_id: str) -> GateResult:
        """Evaluate the §7.3 confidence gate for a task."""
        task = self.get_task(task_id)
        if not task:
            raise AssemblyError(f"Task {task_id} not found")
        return ConfidenceGate.evaluate(task)

    def apply_waiver(
        self,
        task_id: str,
        waiver: Optional[Waiver] = None,
        *,
        parameter: Optional[str] = None,
        rationale: Optional[str] = None,
        waived_by: Optional[str] = None,
        reason: Optional[str] = None,
        approver_name: Optional[str] = None,
        approver_role: Optional[str] = None,
        scope: str = "task",
    ) -> Waiver:
        """Apply a documented waiver to a task.

        Accepts either a pre-built :class:`Waiver` or the individual fields
        (the shape used by the HTTP API). Never accepted for safety-critical
        tasks.
        """
        task = self.get_task(task_id)
        if not task:
            raise AssemblyError(f"Task {task_id} not found")

        if task.safety_critical:
            raise AssemblyError(
                "Cannot waive level-E assumptions on safety-critical tasks"
            )

        if waiver is None:
            resolved_param = parameter or reason
            resolved_rationale = rationale or reason
            resolved_who = waived_by or approver_name or "unknown"
            missing = [n for n, v in (("parameter", resolved_param),
                                      ("rationale", resolved_rationale)) if not v]
            if missing:
                raise AssemblyError(
                    f"apply_waiver requires {', '.join(missing)}"
                )
            waiver = Waiver(
                parameter=resolved_param,
                rationale=resolved_rationale,
                waived_by=resolved_who,
                scope=scope,  # type: ignore[arg-type]
            )

        ConfidenceGate.apply_waiver(task, waiver)
        UTOStateMachine.log_event(
            task, "waiver_applied", waiver.waived_by,
            f"Waiver applied for '{waiver.parameter}'",
            details={"rationale": waiver.rationale, "scope": waiver.scope},
        )

        # Release a task that was parked in `blocked` by the gate, otherwise it
        # would sit there with an open gate and no way to progress.
        if task.status == TaskStatus.BLOCKED and ConfidenceGate.evaluate(task).can_proceed:
            UTOStateMachine.unblock_task(task, actor=waiver.waived_by)
        return waiver

    # ------------------------------------------------------------------ #
    # Audit & persistence
    # ------------------------------------------------------------------ #
    def get_audit_log(self, entity_id: Optional[str] = None) -> list:
        """Audit entries for one entity, or the whole trail."""
        return self.registry.get_audit_log(entity_id=entity_id)

    def export_json(self) -> str:
        """Export registry to JSON."""
        return self.registry.to_json()

    def import_json(self, json_str: str) -> None:
        """Import registry from JSON."""
        self.registry.from_json(json_str)
