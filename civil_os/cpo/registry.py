"""CIVIL-OS project registry — in-memory storage + JSON persistence."""
from __future__ import annotations


import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional


from ..schemas import ECP, Need, Project, Requirement, Site, UTO


if TYPE_CHECKING:
    pass




class ProjectRegistry:
    """In-memory registry for projects, sites, needs, requirements, tasks, ECPs."""


    def __init__(self):
        self.projects: dict[str, Project] = {}
        self.sites: dict[str, Site] = {}
        self.needs: dict[str, Need] = {}
        self.requirements: dict[str, Requirement] = {}
        self.tasks: dict[str, UTO] = {}
        self.ecps: dict[str, ECP] = {}


    # Projects
    def register_project(self, project: Project) -> str:
        """Register a project and return its ID."""
        self.projects[project.project_id] = project
        return project.project_id


    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve a project by ID."""
        return self.projects.get(project_id)


    def list_projects(self) -> list[Project]:
        """List all projects."""
        return list(self.projects.values())


    # Sites
    def register_site(self, site: Site) -> str:
        """Register a site and return its ID."""
        self.sites[site.site_id] = site
        return site.site_id


    def get_site(self, site_id: str) -> Optional[Site]:
        """Retrieve a site by ID."""
        return self.sites.get(site_id)


    def get_sites_for_project(self, project_id: str) -> list[Site]:
        """List all sites for a project."""
        return [s for s in self.sites.values() if s.project_id == project_id]


    # Needs
    def register_need(self, need: Need) -> str:
        """Register a need and return its ID."""
        self.needs[need.need_id] = need
        return need.need_id


    def get_need(self, need_id: str) -> Optional[Need]:
        """Retrieve a need by ID."""
        return self.needs.get(need_id)


    def get_needs_for_project(self, project_id: str) -> list[Need]:
        """List all needs for a project."""
        return [n for n in self.needs.values() if n.project_id == project_id]


    # Requirements
    def register_requirement(self, requirement: Requirement) -> str:
        """Register a requirement and return its ID."""
        self.requirements[requirement.requirement_id] = requirement
        return requirement.requirement_id


    def get_requirement(self, requirement_id: str) -> Optional[Requirement]:
        """Retrieve a requirement by ID."""
        return self.requirements.get(requirement_id)


    def get_requirements_for_project(self, project_id: str) -> list[Requirement]:
        """List all requirements for a project."""
        return [r for r in self.requirements.values() if r.project_id == project_id]


    # Tasks (UTOs)
    def register_task(self, task: UTO) -> str:
        """Register a task and return its ID."""
        self.tasks[task.uto_id] = task
        return task.uto_id


    def get_task(self, task_id: str) -> Optional[UTO]:
        """Retrieve a task by ID."""
        return self.tasks.get(task_id)


    def get_tasks_for_project(self, project_id: str) -> list[UTO]:
        """List all tasks for a project."""
        return [t for t in self.tasks.values() if t.project_id == project_id]


    # ECPs
    def register_ecp(self, ecp: ECP) -> str:
        """Register an ECP and return its ID."""
        self.ecps[ecp.ecp_id] = ecp
        return ecp.ecp_id


    def get_ecp(self, ecp_id: str) -> Optional[ECP]:
        """Retrieve an ECP by ID."""
        return self.ecps.get(ecp_id)


    def get_ecps_for_project(self, project_id: str) -> list[ECP]:
        """List all ECPs for a project."""
        return [e for e in self.ecps.values() if e.project_id == project_id]


    # JSON persistence
    def to_json(self) -> str:
        """Serialize the registry to JSON."""
        data = {
            "projects": [p.model_dump() for p in self.projects.values()],
            "sites": [s.model_dump() for s in self.sites.values()],
            "needs": [n.model_dump() for n in self.needs.values()],
            "requirements": [r.model_dump() for r in self.requirements.values()],
            "tasks": [t.model_dump() for t in self.tasks.values()],
            "ecps": [e.model_dump() for e in self.ecps.values()],
        }
        return json.dumps(data, default=str, indent=2)


    def from_json(self, json_str: str) -> None:
        """Deserialize the registry from JSON."""
        data = json.loads(json_str)


        # Projects
        for pdata in data.get("projects", []):
            p = Project(**pdata)
            self.projects[p.project_id] = p


        # Sites
        for sdata in data.get("sites", []):
            s = Site(**sdata)
            self.sites[s.site_id] = s


        # Needs
        for ndata in data.get("needs", []):
            n = Need(**ndata)
            self.needs[n.need_id] = n


        # Requirements
        for rdata in data.get("requirements", []):
            r = Requirement(**rdata)
            self.requirements[r.requirement_id] = r


        # Tasks
        for tdata in data.get("tasks", []):
            t = UTO(**tdata)
            self.tasks[t.uto_id] = t


        # ECPs
        for edata in data.get("ecps", []):
            e = ECP(**edata)
            self.ecps[e.ecp_id] = e
