"""CIVIL-OS FastAPI Web Application Backend - v0.2"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from civil_os.cpo.orchestrator import CivilProjectOrchestrator
from civil_os.cpo.registry import ProjectRegistry
from civil_os.cpo.state_machine import StateMachineError
from civil_os.engine.assembler import AssemblyError
from civil_os.engine.gates import GateResult
from civil_os.schemas import (
    ConfidenceLevel,
    ECP,
    LifecyclePhase,
    Location,
    Need,
    Project,
    ProjectStatus,
    ProjectType,
    Site,
    TaskStatus,
    UTO,
)

# Global registry and CPO
_registry = ProjectRegistry()
_cpo = CivilProjectOrchestrator(registry=_registry)

# Seed data flag
_SEEDED = False


def _seed_demo_data():
    """Seed the Al-Wadi Industrial Park demo project."""
    global _SEEDED
    if _SEEDED:
        return
    _SEEDED = True

    project = Project(
        name="Al-Wadi Industrial Park",
        description="20,000 m² industrial facility in Riyadh",
        project_type=ProjectType.INDUSTRIAL,
        status=ProjectStatus.ACTIVE,
        design_life_years=50,
        location=Location(
            country="Saudi Arabia",
            region="Riyadh Province",
            municipality="Riyadh",
            latitude=24.7136,
            longitude=46.6753,
            elevation_m=612.0,
        ),
        budget_amount=25000000,
        budget_currency="SAR",
        land_area_available_m2=45000,
        risk_tolerance="moderate",
        current_phase=LifecyclePhase.CONCEPT_DESIGN,
    )
    _registry.register_project(project)

    site = Site(
        project_id=project.project_id,
        name="Al-Wadi Site",
        description="Flat desert terrain, loose sand to 8m, dense sand below",
        terrain={"elevation": 612, "slope": "flat"},
        geology={"rock_type": "sedimentary", "seismic_zone": "Zone 2A"},
        soil_profiles=[],
        hydrology={"groundwater_depth": "3.0m (assumed)"},
        climate={"temperature_range": {"min": 8, "max": 48}},
        hazards=[],
        existing_assets=[],
        data_gaps=["Groundwater verification needed", "Borehole BH-07 pending"],
    )
    _registry.register_site(site)

    need = Need(
        project_id=project.project_id,
        category="infrastructure",
        problem_statement="Provide 20,000 m² industrial facility with drainage",
        affected_population={"count": 500, "description": "Industrial workers"},
        service_gap="No existing facility meets modern standards",
        performance_targets=[],
        social_objectives=["Job creation"],
        economic_objectives=["GDP contribution"],
        environmental_objectives=["Sustainable design"],
        resilience_objectives=["50-year design life"],
        constraints=[],
        success_criteria=["On time", "On budget", "Code compliant"],
        unknowns=["Exact groundwater level"],
        recommended_investigations=["Additional boreholes"],
        confidence_level=ConfidenceLevel.B,
    )
    _registry.register_need(need)

    # Create tasks
    task1 = UTO(
        project_id=project.project_id,
        task_name="Site Characterization Report",
        discipline="geotechnical",
        phase=LifecyclePhase.CONCEPT_DESIGN,
        objective="Characterize site conditions for foundation design",
        status=TaskStatus.COMPLETED,
        assigned_to="agent-site-intelligence",
        review_required=True,
        approval_required=True,
        approval_chain=[
            {
                "role": "Geotechnical Engineer",
                "approver": "Dr. A. Smith",
                "status": "approved",
            }
        ],
    )
    task1.execution_log.append(
        {
            "timestamp": datetime.now(timezone.utc),
            "event": "task_completed",
            "actor": "agent-site-intelligence",
            "details": {"output": "Site characterization report generated"},
        }
    )
    _registry.register_task(task1)

    task2 = UTO(
        project_id=project.project_id,
        task_name="Foundation Type Selection",
        discipline="geotechnical",
        phase=LifecyclePhase.CONCEPT_DESIGN,
        objective="Select optimal foundation system",
        status=TaskStatus.COMPLETED,
        assigned_to="agent-geotechnical",
        review_required=True,
        approval_required=True,
        approval_chain=[
            {"role": "Geotechnical Engineer", "approver": "Dr. A. Smith", "status": "approved"},
            {"role": "Independent Checker", "approver": "Eng. B. Jones", "status": "approved"},
        ],
    )
    _registry.register_task(task2)

    task3 = UTO(
        project_id=project.project_id,
        task_name="Drainage Design",
        discipline="water_resources",
        phase=LifecyclePhase.CONCEPT_DESIGN,
        objective="Design stormwater drainage system",
        status=TaskStatus.IN_PROGRESS,
        assigned_to="agent-civil-systems",
        review_required=True,
        approval_required=True,
    )
    _registry.register_task(task3)

    # Assemble ECP
    from civil_os.engine.assembler import ECPAssembler

    try:
        ecp = ECPAssembler.assemble(
            project=project,
            site=site,
            need=need,
            validity_days=30,
        )
        _registry.register_ecp(ecp)
    except AssemblyError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_demo_data()
    yield


app = FastAPI(
    title="CIVIL-OS",
    description="Civil Engineering Project Intelligence and Execution System",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============ Pydantic Models for API ============


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    project_type: str = "industrial"
    design_life_years: int = 50
    country: str
    region: str = ""
    municipality: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    elevation_m: float = 0.0
    budget_amount: Optional[float] = None
    budget_currency: str = "USD"
    land_area_available_m2: Optional[float] = None
    risk_tolerance: str = "moderate"


class SiteCreate(BaseModel):
    name: str
    description: str = ""
    terrain: Optional[dict] = None
    geology: Optional[dict] = None
    soil_profiles: list = []
    hydrology: Optional[dict] = None
    climate: Optional[dict] = None
    hazards: list = []
    existing_assets: list = []
    data_gaps: list = []


class NeedCreate(BaseModel):
    category: str = "infrastructure"
    problem_statement: str
    affected_population_count: int = 0
    service_gap: str = ""
    confidence_level: str = "B"


class TaskCreate(BaseModel):
    task_name: str
    discipline: str
    phase: str = "concept_design"
    objective: str = ""
    assigned_to: str = ""
    review_required: bool = True
    approval_required: bool = True


class WaiverApply(BaseModel):
    reason: str
    approver_name: str
    approver_role: str


# ============ API Routes ============


@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.2.0",
        "projects": len(_registry.projects),
    }


# ---- Projects ----


@app.get("/api/projects")
async def list_projects():
    projects = _registry.list_projects()
    return {
        "projects": [
            {
                "project_id": p.project_id,
                "name": p.name,
                "description": p.description,
                "project_type": str(p.project_type),
                "status": str(p.status),
                "current_phase": str(p.current_phase),
                "location": {
                    "country": p.location.country if p.location else None,
                    "latitude": p.location.latitude if p.location else None,
                    "longitude": p.location.longitude if p.location else None,
                },
                "budget_amount": p.budget_amount,
                "budget_currency": p.budget_currency,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ]
    }


@app.post("/api/projects")
async def create_project(data: ProjectCreate):
    try:
        ptype = ProjectType(data.project_type.upper())
    except ValueError:
        ptype = ProjectType.INDUSTRIAL

    project = Project(
        name=data.name,
        description=data.description,
        project_type=ptype,
        location=Location(
            country=data.country,
            region=data.region,
            municipality=data.municipality,
            latitude=data.latitude,
            longitude=data.longitude,
            elevation_m=data.elevation_m,
        ),
        budget_amount=data.budget_amount,
        budget_currency=data.budget_currency,
        land_area_available_m2=data.land_area_available_m2,
        risk_tolerance=data.risk_tolerance,
    )
    _registry.register_project(project)
    return {"project_id": project.project_id, "status": "created"}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    project = _registry.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump(mode="json")


# ---- Sites ----


@app.post("/api/projects/{project_id}/sites")
async def create_site(project_id: str, data: SiteCreate):
    project = _registry.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    site = Site(
        project_id=project_id,
        name=data.name,
        description=data.description,
        terrain=data.terrain or {},
        geology=data.geology or {},
        soil_profiles=data.soil_profiles,
        hydrology=data.hydrology or {},
        climate=data.climate or {},
        hazards=data.hazards,
        existing_assets=data.existing_assets,
        data_gaps=data.data_gaps,
    )
    _registry.register_site(site)
    return {"site_id": site.site_id, "status": "created"}


@app.get("/api/projects/{project_id}/sites")
async def get_project_sites(project_id: str):
    sites = _registry.get_sites_for_project(project_id)
    return {"sites": [s.model_dump(mode="json") for s in sites]}


# ---- Needs ----


@app.post("/api/projects/{project_id}/needs")
async def create_need(project_id: str, data: NeedCreate):
    project = _registry.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        cl = ConfidenceLevel(data.confidence_level.upper())
    except ValueError:
        cl = ConfidenceLevel.B

    need = Need(
        project_id=project_id,
        category=data.category,
        problem_statement=data.problem_statement,
        affected_population={"count": data.affected_population_count, "description": ""},
        service_gap=data.service_gap,
        confidence_level=cl,
    )
    _registry.register_need(need)
    return {"need_id": need.need_id, "status": "created"}


@app.get("/api/projects/{project_id}/needs")
async def get_project_needs(project_id: str):
    needs = _registry.get_needs_for_project(project_id)
    return {"needs": [n.model_dump(mode="json") for n in needs]}


# ---- ECPs ----


@app.post("/api/projects/{project_id}/ecps")
async def assemble_ecp(project_id: str, validity_days: int = 30):
    project = _registry.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sites = _registry.get_sites_for_project(project_id)
    site = sites[0] if sites else None

    needs = _registry.get_needs_for_project(project_id)
    need = needs[0] if needs else None

    from civil_os.engine.assembler import ECPAssembler

    try:
        ecp = ECPAssembler.assemble(
            project=project,
            site=site,
            need=need,
            validity_days=validity_days,
        )
        _registry.register_ecp(ecp)
        return {
            "ecp_id": ecp.ecp_id,
            "version": ecp.version,
            "content_hash": ecp.content_hash,
            "assembled_at": ecp.created_at.isoformat() if ecp.created_at else None,
            "valid_until": ecp.validity.valid_until.isoformat() if ecp.validity else None,
            "confidence_summary": ecp.confidence_summary.model_dump(mode="json")
            if ecp.confidence_summary
            else {},
            "applicable_codes": [c.model_dump(mode="json") for c in ecp.applicable_codes],
        }
    except AssemblyError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/projects/{project_id}/ecps")
async def get_project_ecps(project_id: str):
    ecps = _registry.get_ecps_for_project(project_id)
    return {"ecps": [e.model_dump(mode="json") for e in ecps]}


# ---- Tasks ----


@app.get("/api/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str):
    tasks = _registry.get_tasks_for_project(project_id)
    return {
        "tasks": [
            {
                "task_id": t.uto_id,
                "task_name": t.task_name,
                "discipline": t.discipline,
                "phase": str(t.phase),
                "status": str(t.status),
                "objective": t.objective,
                "assigned_to": t.assigned_to,
                "review_required": t.review_required,
                "approval_required": t.approval_required,
                "approval_chain": [a.model_dump(mode="json") for a in t.approval_chain],
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "execution_log": [
                    {
                        "timestamp": e.get("timestamp", datetime.now(timezone.utc)).isoformat()
                        if isinstance(e.get("timestamp"), datetime)
                        else e.get("timestamp"),
                        "event": e.get("event"),
                        "actor": e.get("actor"),
                    }
                    for e in t.execution_log
                ],
            }
            for t in tasks
        ]
    }


@app.post("/api/projects/{project_id}/tasks")
async def create_task(project_id: str, data: TaskCreate):
    project = _registry.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        phase = LifecyclePhase(data.phase.upper())
    except ValueError:
        phase = LifecyclePhase.CONCEPT_DESIGN

    task = UTO(
        project_id=project_id,
        task_name=data.task_name,
        discipline=data.discipline,
        phase=phase,
        objective=data.objective,
        assigned_to=data.assigned_to,
        review_required=data.review_required,
        approval_required=data.approval_required,
    )
    _registry.register_task(task)
    return {"task_id": task.uto_id, "status": "created"}


@app.post("/api/tasks/{task_id}/start")
async def start_task(task_id: str):
    task = _registry.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        _cpo.start_task(task_id)
        return {
            "task_id": task_id,
            "status": str(task.status),
            "message": "Task started",
        }
    except StateMachineError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    task = _registry.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        _cpo.complete_task(task_id)
        return {
            "task_id": task_id,
            "status": str(task.status),
            "message": "Task completed",
        }
    except StateMachineError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, approver_name: str = "", approver_role: str = ""):
    task = _registry.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        _cpo.approve_task(task_id, approver_name=approver_name, approver_role=approver_role)
        return {
            "task_id": task_id,
            "status": str(task.status),
            "message": "Task approved",
        }
    except StateMachineError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/api/tasks/{task_id}/gate")
async def check_gate(task_id: str):
    task = _registry.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = _cpo.check_gate(task_id)
    return {
        "task_id": task_id,
        "can_proceed": result.can_proceed,
        "level": result.level.value if result.level else None,
        "message": result.message,
        "issues": result.issues,
    }


@app.post("/api/tasks/{task_id}/waiver")
async def apply_waiver(task_id: str, data: WaiverApply):
    task = _registry.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        _cpo.apply_waiver(
            task_id,
            reason=data.reason,
            approver_name=data.approver_name,
            approver_role=data.approver_role,
        )
        return {
            "task_id": task_id,
            "status": str(task.status),
            "message": "Waiver applied",
        }
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


# ---- Registry Export ----


@app.get("/api/registry/export")
async def export_registry():
    return json.loads(_registry.to_json())


@app.post("/api/registry/import")
async def import_registry(data: dict):
    _registry.from_json(json.dumps(data))
    return {"status": "imported", "projects": len(_registry.projects)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
