"""TSD-001 §3.2 — Civil Project Orchestrator (CPO)."""
from __future__ import annotations


from typing import TYPE_CHECKING, Optional


from ..engine import ECPAssembler, AssemblyError, ConfidenceGate
from ..schemas import ECP, Need, Project, Requirement, Site, UTO, Waiver
from .registry import ProjectRegistry
from .state_machine import UTOStateMachine, StateMachineError


if TYPE_CHECKING:
    pass




class CivilProjectOrchestrator:
    """§3.2 — main orchestrator for CIVIL-OS project workflow.

    Coordinates:
    - Project / site / need / requirement registration
    - ECP assembly and versioning
    - Task lifecycle and state management
    - Confidence gating and waivers
    """


    def __init__(self):
        self.registry = ProjectRegistry()


    # Project management
    def create_project(
        self,
        name: str,
        project_type: str,
        location: dict,
        **kwargs,
    ) -> Project:
        """Create and register a new project."""
        from ..schemas import Location, ProjectType


        loc = Location(**location)
        project = Project(
            name=name,
            project_type=ProjectType(project_type),
            location=loc,
            **kwargs,
        )
        self.registry.register_project(project)
        return project


    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve a project."""
        return self.registry.get_project(project_id)


    # Site management
    def register_site(self, project_id: str, site: Site) -> str:
        """Register a site for a project."""
        site.project_id = project_id
        return self.registry.register_site(site)


    def get_sites_for_project(self, project_id: str) -> list[Site]:
        """List sites for a project."""
        return self.registry.get_sites_for_project(project_id)


    # Need management
    def register_need(self, project_id: str, need: Need) -> str:
        """Register a need for a project."""
        need.project_id = project_id
        return self.registry.register_need(need)


    def get_needs_for_project(self, project_id: str) -> list[Need]:
        """List needs for a project."""
        return self.registry.get_needs_for_project(project_id)


    # Requirement management
    def register_requirement(self, project_id: str, requirement: Requirement) -> str:
        """Register a requirement for a project."""
        requirement.project_id = project_id
        return self.registry.register_requirement(requirement)


    def get_requirements_for_project(self, project_id: str) -> list[Requirement]:
        """List requirements for a project."""
        return self.registry.get_requirements_for_project(project_id)


    # ECP assembly
    def assemble_ecp(
        self,
        project_id: str,
        site_id: Optional[str] = None,
        need_id: Optional[str] = None,
        validity_days: int = 30,
    ) -> ECP:
        """
        Assemble an ECP for a project (§5).
        Applies assembly rules: completeness, freshness, confidence, versioning, jurisdiction.
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
        )


        self.registry.register_ecp(ecp)
        return ecp


    # Task management
    def create_task(self, project_id: str, ecp_id: str, task_name: str, **kwargs) -> UTO:
        """Create a new task (UTO)."""
        from ..schemas import ECPRef, TaskStatus


        project = self.get_project(project_id)
        if not project:
            raise AssemblyError(f"Project {project_id} not found")


        ecp = self.registry.get_ecp(ecp_id)
        if not ecp:
            raise AssemblyError(f"ECP {ecp_id} not found")


        ecp_ref = ECPRef(ecp_id=ecp.ecp_id, version=ecp.version)
        task = UTO(
            project_id=project_id,
            ecp_ref=ecp_ref,
            task_name=task_name,
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


    # Task lifecycle
    def start_task(self, task_id: str, actor: str = "system") -> None:
        """Start a task (ready → in_progress)."""
        task = self.get_task(task_id)
        if not task:
            raise StateMachineError(f"Task {task_id} not found")


        UTOStateMachine.start_task(task, actor=actor)


    def mark_under_review(self, task_id: str, actor: str = "system") -> None:
        """Mark task for review (in_progress → under_review or auto-approve)."""
        task = self.get_task(task_id)
        if not task:
            raise StateMachineError(f"Task {task_id} not found")


        UTOStateMachine.mark_under_review(task, actor=actor)


    def approve_task(self, task_id: str, actor: str = "system") -> None:
        """Approve a task (under_review → approved)."""
        task = self.get_task(task_id)
        if not task:
            raise StateMachineError(f"Task {task_id} not found")


        UTOStateMachine.approve_task(task, actor=actor)


    def complete_task(self, task_id: str, actor: str = "system") -> None:
        """Complete a task (approved → completed)."""
        task = self.get_task(task_id)
        if not task:
            raise StateMachineError(f"Task {task_id} not found")


        UTOStateMachine.complete_task(task, actor=actor)


    # Confidence gating & waivers
    def check_gate(self, task_id: str) -> tuple[bool, list[str]]:
        """Check if a task can proceed (confidence gate)."""
        task = self.get_task(task_id)
        if not task:
            raise AssemblyError(f"Task {task_id} not found")


        return ConfidenceGate.check_uto(task)


    def apply_waiver(self, task_id: str, waiver: Waiver) -> None:
        """Apply a waiver to a task (if not safety-critical)."""
        task = self.get_task(task_id)
        if not task:
            raise AssemblyError(f"Task {task_id} not found")


        if task.safety_critical:
            raise AssemblyError("Cannot waive level-E assumptions on safety-critical tasks")


        ConfidenceGate.apply_waiver(task, waiver)


    # Persistence
    def export_json(self) -> str:
        """Export registry to JSON."""
        return self.registry.to_json()


    def import_json(self, json_str: str) -> None:
        """Import registry from JSON."""
        self.registry.from_json(json_str)
