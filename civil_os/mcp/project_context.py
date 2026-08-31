"""TSD-001 §8.2 — mcp-project server: project context tools & resources."""
from __future__ import annotations


from typing import TYPE_CHECKING, Optional


from ..cpo import CivilProjectOrchestrator
from ..schemas import Location, Need, Requirement, Site
from .server import MCPServer


if TYPE_CHECKING:
    pass




def create_mcp_project_server(cpo: CivilProjectOrchestrator) -> MCPServer:
    """
    Create the §8.2 mcp-project server with tools for project context assembly.

    Tools:
    - create_project: register a project
    - register_site: register a site
    - register_need: register a need
    - register_requirement: register a requirement
    - assemble_ecp: assemble an ECP
    - create_task: create a task
    - start_task: start a task
    - check_gate: check confidence gate
    - apply_waiver: apply a waiver
    - list_projects: list all projects
    - export_json: export the registry to JSON
    """


    server = MCPServer(name="mcp-project", version="0.1.0")


    # Tool handlers
    def handle_create_project(name: str, project_type: str, country: str, 
                             latitude: float, longitude: float, **kwargs) -> dict:
        project = cpo.create_project(
            name=name,
            project_type=project_type,
            location={
                "country": country,
                "latitude": latitude,
                "longitude": longitude,
                **{k: v for k, v in kwargs.items() 
                   if k in ["region", "municipality", "elevation_m"]},
            },
            **{k: v for k, v in kwargs.items() 
               if k in ["description", "design_life_years", "budget_amount",
                       "target_completion", "land_area_available_m2", "risk_tolerance"]},
        )
        return {"project_id": project.project_id, "name": project.name}


    def handle_register_site(project_id: str, boundary: Optional[dict] = None, **kwargs) -> dict:
        site = Site(
            project_id=project_id,
            boundary=boundary,
            **{k: v for k, v in kwargs.items() 
               if k in ["terrain", "geology", "soil_profiles", "hydrology", 
                       "climate", "hazards", "existing_assets", "constraints",
                       "data_gaps", "recommended_investigations"]},
        )
        site_id = cpo.register_site(project_id, site)
        return {"site_id": site_id}


    def handle_register_need(project_id: str, category: str, problem_statement: str, 
                           **kwargs) -> dict:
        need = Need(
            project_id=project_id,
            category=category,
            problem_statement=problem_statement,
            **{k: v for k, v in kwargs.items() 
               if k in ["affected_population", "service_gap", "current_demand",
                       "future_demand", "performance_targets", "social_objectives",
                       "economic_objectives", "environmental_objectives",
                       "resilience_objectives", "constraints", "success_criteria"]},
        )
        need_id = cpo.register_need(project_id, need)
        return {"need_id": need_id}


    def handle_register_requirement(project_id: str, discipline: str, category: str,
                                  description: str, **kwargs) -> dict:
        requirement = Requirement(
            project_id=project_id,
            discipline=discipline,
            category=category,
            description=description,
            **{k: v for k, v in kwargs.items() 
               if k in ["priority", "verification_method", "acceptance_criteria",
                       "allocated_to", "status", "traceability", "change_history",
                       "confidence_level"]},
        )
        req_id = cpo.register_requirement(project_id, requirement)
        return {"requirement_id": req_id}


    def handle_assemble_ecp(project_id: str, site_id: Optional[str] = None,
                          need_id: Optional[str] = None, validity_days: int = 30) -> dict:
        ecp = cpo.assemble_ecp(project_id, site_id=site_id, need_id=need_id,
                              validity_days=validity_days)
        return {
            "ecp_id": ecp.ecp_id,
            "version": ecp.version,
            "valid_until": str(ecp.validity.valid_until),
        }


    def handle_create_task(project_id: str, ecp_id: str, task_name: str,
                         discipline: str, **kwargs) -> dict:
        task = cpo.create_task(project_id, ecp_id, task_name, discipline=discipline,
                              **{k: v for k, v in kwargs.items() 
                                 if k in ["description", "task_type", "phase", 
                                         "priority", "safety_critical", "dependencies",
                                         "inputs", "requirements_satisfied", "assumptions"]})
        return {"task_id": task.uto_id, "status": task.status}


    def handle_start_task(task_id: str, actor: str = "system") -> dict:
        cpo.start_task(task_id, actor=actor)
        task = cpo.get_task(task_id)
        return {"task_id": task_id, "status": task.status}


    def handle_check_gate(task_id: str) -> dict:
        can_proceed, issues = cpo.check_gate(task_id)
        return {"can_proceed": can_proceed, "issues": issues}


    def handle_apply_waiver(task_id: str, parameter: str, rationale: str,
                          waived_by: str) -> dict:
        from ..schemas import Waiver
        waiver = Waiver(parameter=parameter, rationale=rationale, waived_by=waived_by)
        cpo.apply_waiver(task_id, waiver)
        return {"task_id": task_id, "waiver_applied": True}


    def handle_list_projects() -> dict:
        projects = cpo.registry.list_projects()
        return {
            "projects": [
                {"project_id": p.project_id, "name": p.name, "status": p.status}
                for p in projects
            ]
        }


    def handle_export_json() -> dict:
        json_str = cpo.export_json()
        return {"json": json_str}


    # Register tools
    server.register_tool(
        "create_project",
        "Register a new project",
        handle_create_project,
        required_args=["name", "project_type", "country", "latitude", "longitude"],
    )
    server.register_tool(
        "register_site",
        "Register a site for a project",
        handle_register_site,
        required_args=["project_id"],
    )
    server.register_tool(
        "register_need",
        "Register a need for a project",
        handle_register_need,
        required_args=["project_id", "category", "problem_statement"],
    )
    server.register_tool(
        "register_requirement",
        "Register a requirement for a project",
        handle_register_requirement,
        required_args=["project_id", "discipline", "category", "description"],
    )
    server.register_tool(
        "assemble_ecp",
        "Assemble an Engineering Context Packet",
        handle_assemble_ecp,
        required_args=["project_id"],
    )
    server.register_tool(
        "create_task",
        "Create a task for a project",
        handle_create_task,
        required_args=["project_id", "ecp_id", "task_name", "discipline"],
    )
    server.register_tool(
        "start_task",
        "Start a task",
        handle_start_task,
        required_args=["task_id"],
    )
    server.register_tool(
        "check_gate",
        "Check confidence gate for a task",
        handle_check_gate,
        required_args=["task_id"],
    )
    server.register_tool(
        "apply_waiver",
        "Apply a waiver to a task",
        handle_apply_waiver,
        required_args=["task_id", "parameter", "rationale", "waived_by"],
    )
    server.register_tool(
        "list_projects",
        "List all projects",
        handle_list_projects,
    )
    server.register_tool(
        "export_json",
        "Export the registry to JSON",
        handle_export_json,
    )


    return server
