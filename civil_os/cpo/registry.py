"""CIVIL-OS project registry — in-memory storage, audit trail, JSON persistence.

Thread safety: every mutation runs under a re-entrant lock so concurrent
registrations cannot interleave and produce duplicate or lost entries
(ROADMAP-001 P1-S1-04).
"""
from __future__ import annotations

import json
import threading
from typing import Any, Optional

from ..schemas import ECP, UTO, AuditEntry, Need, Project, Requirement, Site


class ProjectRegistry:
    """In-memory registry for projects, sites, needs, requirements, tasks, ECPs."""

    def __init__(self):
        self._lock = threading.RLock()
        self.projects: dict[str, Project] = {}
        self.sites: dict[str, Site] = {}
        self.needs: dict[str, Need] = {}
        self.requirements: dict[str, Requirement] = {}
        self.tasks: dict[str, UTO] = {}
        self.ecps: dict[str, ECP] = {}
        self.audit: list[AuditEntry] = []

    # ------------------------------------------------------------------ #
    # Audit trail (TSD-001 §14, ROADMAP-001 P1-S3-01 / P1-S3-02)
    # ------------------------------------------------------------------ #
    def record_audit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str = "system",
        before: Optional[dict] = None,
        after: Optional[dict] = None,
        reason: str = "",
    ) -> AuditEntry:
        """Append an immutable audit entry and return it."""
        entry = AuditEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            before=before,
            after=after,
            reason=reason,
        )
        with self._lock:
            self.audit.append(entry)
        return entry

    def get_audit_log(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> list[AuditEntry]:
        """Audit entries, newest last, optionally filtered by entity."""
        with self._lock:
            entries = list(self.audit)
        if entity_id is not None:
            entries = [e for e in entries if e.entity_id == entity_id]
        if entity_type is not None:
            entries = [e for e in entries if e.entity_type == entity_type]
        return entries

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #
    def register_project(self, project: Project) -> str:
        """Register a project and return its ID."""
        with self._lock:
            self.projects[project.project_id] = project
        self.record_audit("project", project.project_id, "registered", after=project.model_dump(mode="json"))
        return project.project_id

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve a project by ID."""
        with self._lock:
            return self.projects.get(project_id)

    def update_project(self, project: Project, actor: str = "system", reason: str = "",
                       before: Optional[dict] = None) -> str:
        """Replace a project, recording before/after state in the audit trail.

        ``before`` may be supplied by callers that mutate the live object in
        place; without it the snapshot would already reflect the new values.
        """
        with self._lock:
            previous = self.projects.get(project.project_id)
            if before is None:
                before = previous.model_dump(mode="json") if previous else None
            project.touch()
            self.projects[project.project_id] = project
        self.record_audit("project", project.project_id, "updated", actor=actor,
                          before=before, after=project.model_dump(mode="json"), reason=reason)
        return project.project_id

    def list_projects(self) -> list[Project]:
        """List all projects."""
        with self._lock:
            return list(self.projects.values())

    # ------------------------------------------------------------------ #
    # Sites
    # ------------------------------------------------------------------ #
    def register_site(self, site: Site) -> str:
        """Register a site and return its ID."""
        with self._lock:
            self.sites[site.site_id] = site
        self.record_audit("site", site.site_id, "registered", after=site.model_dump(mode="json"))
        return site.site_id

    def update_site(self, site: Site, actor: str = "system", reason: str = "") -> str:
        """Replace a site, recording before/after state in the audit trail."""
        with self._lock:
            previous = self.sites.get(site.site_id)
            before = previous.model_dump(mode="json") if previous else None
            self.sites[site.site_id] = site
        self.record_audit("site", site.site_id, "updated", actor=actor,
                          before=before, after=site.model_dump(mode="json"), reason=reason)
        return site.site_id

    def get_site(self, site_id: str) -> Optional[Site]:
        """Retrieve a site by ID."""
        with self._lock:
            return self.sites.get(site_id)

    def get_sites_for_project(self, project_id: str) -> list[Site]:
        """List all sites for a project."""
        with self._lock:
            return [s for s in self.sites.values() if s.project_id == project_id]

    # ------------------------------------------------------------------ #
    # Needs
    # ------------------------------------------------------------------ #
    def register_need(self, need: Need) -> str:
        """Register a need and return its ID."""
        with self._lock:
            self.needs[need.need_id] = need
        self.record_audit("need", need.need_id, "registered", after=need.model_dump(mode="json"))
        return need.need_id

    def get_need(self, need_id: str) -> Optional[Need]:
        """Retrieve a need by ID."""
        with self._lock:
            return self.needs.get(need_id)

    def get_needs_for_project(self, project_id: str) -> list[Need]:
        """List all needs for a project."""
        with self._lock:
            return [n for n in self.needs.values() if n.project_id == project_id]

    # ------------------------------------------------------------------ #
    # Requirements
    # ------------------------------------------------------------------ #
    def register_requirement(self, requirement: Requirement) -> str:
        """Register a requirement and return its ID."""
        with self._lock:
            self.requirements[requirement.requirement_id] = requirement
        self.record_audit("requirement", requirement.requirement_id, "registered",
                          after=requirement.model_dump(mode="json"))
        return requirement.requirement_id

    def get_requirement(self, requirement_id: str) -> Optional[Requirement]:
        """Retrieve a requirement by ID."""
        with self._lock:
            return self.requirements.get(requirement_id)

    def get_requirements_for_project(self, project_id: str) -> list[Requirement]:
        """List all requirements for a project."""
        with self._lock:
            return [r for r in self.requirements.values() if r.project_id == project_id]

    # ------------------------------------------------------------------ #
    # Tasks (UTOs)
    # ------------------------------------------------------------------ #
    def register_task(self, task: UTO) -> str:
        """Register a task and return its ID."""
        with self._lock:
            self.tasks[task.uto_id] = task
        self.record_audit("task", task.uto_id, "registered", after=task.model_dump(mode="json"))
        return task.uto_id

    def get_task(self, task_id: str) -> Optional[UTO]:
        """Retrieve a task by ID."""
        with self._lock:
            return self.tasks.get(task_id)

    def get_tasks_for_project(self, project_id: str) -> list[UTO]:
        """List all tasks for a project."""
        with self._lock:
            return [t for t in self.tasks.values() if t.project_id == project_id]

    # ------------------------------------------------------------------ #
    # ECPs
    # ------------------------------------------------------------------ #
    def register_ecp(self, ecp: ECP) -> str:
        """Register an ECP and return its ID."""
        with self._lock:
            self.ecps[ecp.ecp_id] = ecp
        return ecp.ecp_id

    def get_ecp(self, ecp_id: str) -> Optional[ECP]:
        """Retrieve an ECP by ID."""
        with self._lock:
            return self.ecps.get(ecp_id)

    def get_ecps_for_project(self, project_id: str) -> list[ECP]:
        """List all ECPs for a project."""
        with self._lock:
            return [e for e in self.ecps.values() if e.project_id == project_id]

    # ------------------------------------------------------------------ #
    # JSON persistence (ROADMAP-001 P1-S1-01)
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        """JSON-ready snapshot of the whole registry.

        Uses ``mode="json"`` so datetimes become ISO-8601 strings and enums
        become their values. Serialising in Python mode and falling back to
        ``str()`` loses type fidelity on round-trip (notably for the
        free-form ``execution_log`` payloads).
        """
        with self._lock:
            return {
                "projects": [p.model_dump(mode="json") for p in self.projects.values()],
                "sites": [s.model_dump(mode="json") for s in self.sites.values()],
                "needs": [n.model_dump(mode="json") for n in self.needs.values()],
                "requirements": [r.model_dump(mode="json") for r in self.requirements.values()],
                "tasks": [t.model_dump(mode="json") for t in self.tasks.values()],
                "ecps": [e.model_dump(mode="json") for e in self.ecps.values()],
                "audit": [a.model_dump(mode="json") for a in self.audit],
            }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the registry to JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def from_json(self, json_str: str) -> None:
        """Replace registry contents from a JSON snapshot."""
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise ValueError("Registry JSON must be an object")

        # Build everything first so a bad payload cannot leave a half-loaded
        # registry behind.
        projects = {p.project_id: p for p in (Project(**d) for d in data.get("projects", []))}
        sites = {s.site_id: s for s in (Site(**d) for d in data.get("sites", []))}
        needs = {n.need_id: n for n in (Need(**d) for d in data.get("needs", []))}
        requirements = {r.requirement_id: r
                        for r in (Requirement(**d) for d in data.get("requirements", []))}
        tasks = {t.uto_id: t for t in (UTO(**d) for d in data.get("tasks", []))}
        ecps = {e.ecp_id: e for e in (ECP(**d) for d in data.get("ecps", []))}
        audit = [AuditEntry(**d) for d in data.get("audit", [])]

        with self._lock:
            self.projects = projects
            self.sites = sites
            self.needs = needs
            self.requirements = requirements
            self.tasks = tasks
            self.ecps = ecps
            self.audit = audit
