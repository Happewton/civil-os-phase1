"""CIVIL-OS HTTP service (TSD-001 v0.2 §20.2 "CPO Service", §24 API contract).

Implements the §24.1 REST surface, the §24.3 error envelope and the §25.1 error
taxonomy on top of the Phase-1 orchestrator.

Run locally with::

    uvicorn app.api:app --reload
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from civil_os.cpo import CivilProjectOrchestrator, GateBlocked, ProjectRegistry
from civil_os.cpo.state_machine import StateMachineError
from civil_os.engine.assembler import AssemblyError
from civil_os.engine.validator import ValidationError as ECPValidationError
from civil_os.schemas import (
    UTO,
    Boundary,
    ClimateData,
    ExistingAsset,
    Geology,
    Hazard,
    Hydrology,
    Need,
    Project,
    Requirement,
    Site,
    SiteConstraint,
    SoilProfile,
)

APP_VERSION = "0.2.0"
STATIC_DIR = Path(__file__).parent / "static"


# --------------------------------------------------------------------------- #
# §24.3 Error envelope / §25.1 Error taxonomy
# --------------------------------------------------------------------------- #
ERROR_STATUS = {
    "VALIDATION_ERROR": 400,
    "ASSEMBLY_ERROR": 422,
    "STATE_MACHINE_ERROR": 409,
    "GATE_BLOCKED": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
}


def error_body(code: str, message: str, detail: Optional[dict] = None) -> dict:
    """Build the §24.3 error envelope."""
    return {
        "error": {
            "code": code,
            "message": message,
            "detail": detail or {},
            "request_id": f"req-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


def error_response(code: str, message: str, detail: Optional[dict] = None) -> JSONResponse:
    return JSONResponse(status_code=ERROR_STATUS.get(code, 400),
                        content=error_body(code, message, detail))


# --------------------------------------------------------------------------- #
# Application state
# --------------------------------------------------------------------------- #
def _truthy(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_orchestrator() -> CivilProjectOrchestrator:
    """Create a CPO over a fresh registry."""
    return CivilProjectOrchestrator(registry=ProjectRegistry())


def seed_demo_data(cpo: CivilProjectOrchestrator) -> dict:
    """Register the Al-Wadi demo project so a fresh instance has content."""
    from civil_os.schemas import (
        AffectedPopulation,
        ConfidenceLevel,
        Location,
        ParameterEvidence,
        ProjectType,
        SoilLayer,
        SoilProfile,
    )

    project = Project(
        name="Al-Wadi Flood Protection",
        description="Flood protection for 10,000 residents (TSD-001 §3.3)",
        project_type=ProjectType.water,
        location=Location(country="SA", region="Riyadh Province",
                          municipality="Al-Wadi", latitude=24.7136,
                          longitude=46.6753, elevation_m=612.0),
        budget_amount=15_000_000,
        budget_currency="SAR",
        risk_tolerance="conservative",
    )
    cpo.registry.register_project(project)

    site = Site(
        project_id=project.project_id,
        name="Al-Wadi catchment",
        geology=Geology(rock_types=["silty sand"], seismic_zone="SBC 401 Zone 2A"),
        hydrology=Hydrology(
            catchment_area_km2=12.4,
            return_period_years=100,
            groundwater_level=ParameterEvidence(
                parameter="groundwater_level", value=5.2, unit="m",
                source="Regional groundwater study (unverified)",
                confidence_level=ConfidenceLevel.E,
            ),
        ),
        soil_profiles=[SoilProfile(
            borehole_id="BH-07",
            layers=[SoilLayer(depth_from_m=0.0, depth_to_m=5.0,
                              soil_type="silty sand", classification="SP-SM",
                              confidence_level=ConfidenceLevel.E)],
        )],
        data_gaps=["Flood inundation modelling for the 100-year event"],
        recommended_investigations=["Geotechnical site investigation (SPT boreholes)"],
    )
    cpo.register_site(project.project_id, site)

    need = Need(
        project_id=project.project_id,
        category="safety",
        problem_statement="Protect 10,000 residents from seasonal 100-year flooding",
        affected_population=AffectedPopulation(
            count=10_000, description="Al-Wadi settlement residents",
            vulnerable_groups=["children", "elderly", "disabled"],
        ),
        confidence_level=ConfidenceLevel.B,
    )
    cpo.register_need(project.project_id, need)

    ecp = cpo.assemble_ecp(
        project_id=project.project_id,
        site_id=site.site_id,
        need_id=need.need_id,
        validity_days=30,
    )
    return {"project_id": project.project_id, "site_id": site.site_id,
            "need_id": need.need_id, "ecp_id": ecp.ecp_id}


cpo = build_orchestrator()
SEED_ON_START = _truthy(os.environ.get("CIVIL_OS_SEED"), default=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if SEED_ON_START and not cpo.registry.list_projects():
        seed_demo_data(cpo)
    yield


app = FastAPI(
    title="CIVIL-OS",
    description="Civil Engineering Project Intelligence and Execution System",
    version=APP_VERSION,
    lifespan=lifespan,
)

# §19.5: whitelist-only CORS, no wildcards. Configure with CIVIL_OS_CORS_ORIGINS
# (comma-separated). Wildcards are ignored because they are unsafe with
# credentials.
_allowed = [o.strip() for o in os.environ.get("CIVIL_OS_CORS_ORIGINS", "").split(",") if o.strip()]
_allowed = [o for o in _allowed if o != "*"]
if _allowed:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )


# --------------------------------------------------------------------------- #
# Exception handlers → §24.3 envelope
# --------------------------------------------------------------------------- #
@app.exception_handler(AssemblyError)
async def _assembly_error(request: Request, exc: AssemblyError):
    return error_response("ASSEMBLY_ERROR", str(exc))


@app.exception_handler(ECPValidationError)
async def _ecp_validation_error(request: Request, exc: ECPValidationError):
    return error_response("ASSEMBLY_ERROR", str(exc), {"rule": "r.2"})


@app.exception_handler(GateBlocked)
async def _gate_blocked(request: Request, exc: GateBlocked):
    return error_response("GATE_BLOCKED", str(exc), {"issues": exc.issues})


@app.exception_handler(StateMachineError)
async def _state_machine_error(request: Request, exc: StateMachineError):
    return error_response("STATE_MACHINE_ERROR", str(exc))


@app.exception_handler(RequestValidationError)
async def _request_validation_error(request: Request, exc: RequestValidationError):
    return error_response("VALIDATION_ERROR", "Request payload failed validation",
                          {"errors": _jsonable_errors(exc)})


@app.exception_handler(ValidationError)
async def _model_validation_error(request: Request, exc: ValidationError):
    """Domain-model validation (e.g. an unknown category) is a client error."""
    return error_response("VALIDATION_ERROR", "Payload failed domain validation",
                          {"errors": _jsonable_errors(exc)})


def _jsonable_errors(exc: RequestValidationError) -> list[dict]:
    cleaned = []
    for err in exc.errors():
        entry = {k: v for k, v in err.items() if k != "ctx"}
        entry["loc"] = [str(p) for p in err.get("loc", ())]
        ctx = err.get("ctx")
        if ctx:
            entry["ctx"] = {k: str(v) for k, v in ctx.items()}
        cleaned.append(entry)
    return cleaned


# --------------------------------------------------------------------------- #
# Request models (§24.1)
# --------------------------------------------------------------------------- #
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    project_type: str = "water"
    design_life_years: int = Field(50, ge=1, le=200)
    country: str = Field(..., min_length=2, max_length=2)
    region: str = ""
    municipality: str = ""
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    budget_amount: Optional[float] = Field(None, ge=0)
    budget_currency: str = "USD"
    land_area_available_m2: Optional[float] = Field(None, ge=0)
    risk_tolerance: str = "moderate"


class ProjectPatch(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    design_life_years: Optional[int] = Field(None, ge=1, le=200)
    budget_amount: Optional[float] = Field(None, ge=0)
    risk_tolerance: Optional[str] = None
    current_phase: Optional[str] = None
    reason: str = ""


class SiteCreate(BaseModel):
    name: str = "Site"
    description: str = ""
    boundary: Optional[Boundary] = None
    terrain: dict = Field(default_factory=dict)
    geology: Optional[Geology] = None
    soil_profiles: list[SoilProfile] = Field(default_factory=list)
    hydrology: Optional[Hydrology] = None
    climate: Optional[ClimateData] = None
    hazards: list[Hazard] = Field(default_factory=list)
    existing_assets: list[ExistingAsset] = Field(default_factory=list)
    constraints: list[SiteConstraint] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    recommended_investigations: list[str] = Field(default_factory=list)


class NeedCreate(BaseModel):
    category: str = "infrastructure"
    problem_statement: str = Field(..., min_length=1)
    affected_population_count: int = Field(0, ge=0)
    affected_population_description: str = ""
    service_gap: str = ""
    confidence_level: str = "B"


class RequirementCreate(BaseModel):
    discipline: str
    category: str = "functional"
    description: str = Field(..., min_length=1)
    priority: str = "desirable"
    verification_method: str = "analysis"
    acceptance_criteria: str = ""
    allocated_to: str = ""


class TaskCreate(BaseModel):
    project_id: str
    ecp_id: Optional[str] = None
    task_name: str = Field(..., min_length=1)
    discipline: str = "civil"
    task_type: str = "design"
    description: str = ""
    phase: str = ""
    priority: str = "medium"
    safety_critical: bool = False
    requires_review: bool = True
    assumptions: list[dict] = Field(default_factory=list)
    dependencies: list[dict] = Field(default_factory=list)


class ApprovalIn(BaseModel):
    approver_name: str = ""
    approver_role: str = ""
    comments: str = ""


class ReasonIn(BaseModel):
    reason: str = ""


class WaiverApply(BaseModel):
    parameter: str
    rationale: str = Field(..., min_length=10)
    waived_by: str
    scope: str = "task"


# --------------------------------------------------------------------------- #
# Health & MCP introspection
# --------------------------------------------------------------------------- #
@app.get("/api/v1/health", tags=["ops"])
@app.get("/api/health", tags=["ops"])
def health() -> dict:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "projects": len(cpo.registry.list_projects()),
    }


@app.get("/api/v1/mcp/specification", tags=["ops"])
def mcp_specification() -> dict:
    """Expose the §8 mcp-project tool contract as served by this instance."""
    from civil_os.mcp import create_mcp_project_server

    return create_mcp_project_server(cpo).specification()


# --------------------------------------------------------------------------- #
# Projects (§24.1)
# --------------------------------------------------------------------------- #
@app.get("/api/v1/projects", tags=["projects"])
@app.get("/api/projects", tags=["projects"])
def list_projects() -> dict:
    return {"projects": [p.model_dump(mode="json") for p in cpo.list_projects()]}


@app.post("/api/v1/projects", status_code=201, tags=["projects"])
@app.post("/api/projects", status_code=201, tags=["projects"])
def create_project(data: ProjectCreate) -> dict:
    project = cpo.create_project(
        name=data.name,
        project_type=data.project_type,
        country=data.country,
        latitude=data.latitude,
        longitude=data.longitude,
        region=data.region,
        municipality=data.municipality,
        elevation_m=data.elevation_m,
        description=data.description,
        design_life_years=data.design_life_years,
        budget_amount=data.budget_amount,
        budget_currency=data.budget_currency,
        land_area_available_m2=data.land_area_available_m2,
        risk_tolerance=data.risk_tolerance,
    )
    return {"project_id": project.project_id, "name": project.name,
            "status": "created", "project": project.model_dump(mode="json")}


def _require_project(project_id: str) -> Project:
    project = cpo.get_project(project_id)
    if project is None:
        raise _NotFound(f"Project {project_id} not found")
    return project


@app.get("/api/v1/projects/{project_id}", tags=["projects"])
@app.get("/api/projects/{project_id}", tags=["projects"])
def get_project(project_id: str) -> dict:
    return _require_project(project_id).model_dump(mode="json")


@app.patch("/api/v1/projects/{project_id}", tags=["projects"])
def patch_project(project_id: str, data: ProjectPatch, actor: str = Query("api")) -> dict:
    """Update a project; every change is written to the §14 audit trail."""
    project = _require_project(project_id)
    # Snapshot before mutating: the registry holds this same object.
    before = project.model_dump(mode="json")
    reason = data.reason
    for field in ("description", "status", "design_life_years", "budget_amount",
                  "risk_tolerance", "current_phase"):
        value = getattr(data, field)
        if value is not None:
            setattr(project, field, value)
    cpo.update_project(project, actor=actor, reason=reason, before=before)
    return project.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Sites / needs / requirements
# --------------------------------------------------------------------------- #
@app.post("/api/v1/projects/{project_id}/sites", status_code=201, tags=["sites"])
@app.post("/api/projects/{project_id}/sites", status_code=201, tags=["sites"])
def create_site(project_id: str, data: SiteCreate) -> dict:
    _require_project(project_id)
    # SITE sub-records are non-optional models, so fall back to their defaults
    # rather than passing None.
    site = Site(
        project_id=project_id,
        name=data.name,
        description=data.description,
        boundary=data.boundary,
        geology=data.geology or Geology(),
        soil_profiles=data.soil_profiles,
        hydrology=data.hydrology or Hydrology(),
        climate=data.climate or ClimateData(),
        hazards=data.hazards,
        existing_assets=data.existing_assets,
        constraints=data.constraints,
        data_gaps=data.data_gaps,
        recommended_investigations=data.recommended_investigations,
    )
    site_id = cpo.register_site(project_id, site)
    return {"site_id": site_id, "status": "created"}


@app.get("/api/v1/projects/{project_id}/sites", tags=["sites"])
@app.get("/api/projects/{project_id}/sites", tags=["sites"])
def get_project_sites(project_id: str) -> dict:
    _require_project(project_id)
    return {"sites": [s.model_dump(mode="json")
                      for s in cpo.get_sites_for_project(project_id)]}


@app.post("/api/v1/projects/{project_id}/needs", status_code=201, tags=["needs"])
@app.post("/api/projects/{project_id}/needs", status_code=201, tags=["needs"])
def create_need(project_id: str, data: NeedCreate) -> dict:
    from civil_os.schemas import AffectedPopulation

    _require_project(project_id)
    # ``category`` and ``confidence_level`` are validated by the domain model;
    # an unknown value surfaces as a 400 VALIDATION_ERROR.
    need = Need(
        project_id=project_id,
        category=data.category,
        problem_statement=data.problem_statement,
        affected_population=AffectedPopulation(
            count=data.affected_population_count,
            description=data.affected_population_description,
        ),
        service_gap=data.service_gap,
        confidence_level=data.confidence_level,
    )
    need_id = cpo.register_need(project_id, need)
    return {"need_id": need_id, "status": "created"}


@app.get("/api/v1/projects/{project_id}/needs", tags=["needs"])
@app.get("/api/projects/{project_id}/needs", tags=["needs"])
def get_project_needs(project_id: str) -> dict:
    _require_project(project_id)
    return {"needs": [n.model_dump(mode="json")
                      for n in cpo.get_needs_for_project(project_id)]}


@app.post("/api/v1/projects/{project_id}/requirements", status_code=201, tags=["requirements"])
def create_requirement(project_id: str, data: RequirementCreate) -> dict:
    _require_project(project_id)
    requirement = Requirement(
        project_id=project_id,
        discipline=data.discipline,
        category=data.category,
        description=data.description,
        priority=data.priority,
        verification_method=data.verification_method,
        acceptance_criteria=data.acceptance_criteria,
        allocated_to=data.allocated_to,
    )
    requirement_id = cpo.register_requirement(project_id, requirement)
    return {"requirement_id": requirement_id, "status": "created"}


@app.get("/api/v1/projects/{project_id}/requirements", tags=["requirements"])
def get_project_requirements(project_id: str) -> dict:
    _require_project(project_id)
    return {"requirements": [r.model_dump(mode="json")
                             for r in cpo.get_requirements_for_project(project_id)]}


# --------------------------------------------------------------------------- #
# ECPs (§24.1)
# --------------------------------------------------------------------------- #
@app.post("/api/v1/projects/{project_id}/ecps", tags=["ecp"])
@app.post("/api/projects/{project_id}/ecps", tags=["ecp"])
def assemble_ecp(project_id: str, site_id: Optional[str] = None,
                 need_id: Optional[str] = None, validity_days: int = 30) -> dict:
    _require_project(project_id)
    if validity_days < 1:
        return error_response("VALIDATION_ERROR", "validity_days must be >= 1")
    ecp = cpo.assemble_ecp(project_id, site_id=site_id, need_id=need_id,
                           validity_days=validity_days)
    return ecp.model_dump(mode="json")


@app.get("/api/v1/projects/{project_id}/ecps", tags=["ecp"])
@app.get("/api/projects/{project_id}/ecps", tags=["ecp"])
def get_project_ecps(project_id: str) -> dict:
    _require_project(project_id)
    return {"ecps": [e.model_dump(mode="json")
                     for e in cpo.get_ecps_for_project(project_id)]}


@app.get("/api/v1/ecps/{ecp_id}", tags=["ecp"])
def get_ecp(ecp_id: str) -> dict:
    ecp = cpo.get_ecp(ecp_id)
    if ecp is None:
        raise _NotFound(f"ECP {ecp_id} not found")
    return ecp.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Tasks (§24.1)
# --------------------------------------------------------------------------- #
@app.post("/api/v1/tasks", status_code=201, tags=["tasks"])
@app.post("/api/v1/projects/{project_id}/tasks", status_code=201, tags=["tasks"])
@app.post("/api/projects/{project_id}/tasks", status_code=201, tags=["tasks"])
def create_task(
    data: TaskCreate,
    project_id: Optional[str] = None,
) -> dict:
    from civil_os.schemas import TaskDependency

    resolved_project = project_id or data.project_id
    _require_project(resolved_project)

    kwargs: dict[str, Any] = {
        "description": data.description,
        "task_type": data.task_type,
        "phase": data.phase,
        "priority": data.priority,
        "safety_critical": data.safety_critical,
        "requires_review": data.requires_review,
    }
    if data.assumptions:
        try:
            kwargs["assumptions"] = [dict(a) for a in data.assumptions]
        except (TypeError, ValidationError) as exc:
            return error_response("VALIDATION_ERROR", f"Invalid assumptions: {exc}")
    if data.dependencies:
        try:
            kwargs["dependencies"] = [TaskDependency(**d) for d in data.dependencies]
        except ValidationError as exc:
            return error_response("VALIDATION_ERROR", f"Invalid dependencies: {exc}")

    task = cpo.create_task(
        project_id=resolved_project,
        ecp_id=data.ecp_id,
        task_name=data.task_name,
        discipline=data.discipline,
        **kwargs,
    )
    return {"task_id": task.uto_id, "status": task.status,
            "task": task.model_dump(mode="json")}


def _require_task(task_id: str) -> UTO:
    task = cpo.get_task(task_id)
    if task is None:
        raise _NotFound(f"Task {task_id} not found")
    return task


@app.get("/api/v1/tasks/{task_id}", tags=["tasks"])
@app.get("/api/tasks/{task_id}", tags=["tasks"])
def get_task(task_id: str) -> dict:
    return _require_task(task_id).model_dump(mode="json")


@app.get("/api/v1/projects/{project_id}/tasks", tags=["tasks"])
@app.get("/api/projects/{project_id}/tasks", tags=["tasks"])
def get_project_tasks(project_id: str) -> dict:
    _require_project(project_id)
    return {"tasks": [t.model_dump(mode="json")
                      for t in cpo.get_tasks_for_project(project_id)]}


@app.post("/api/v1/tasks/{task_id}/start", tags=["tasks"])
@app.post("/api/tasks/{task_id}/start", tags=["tasks"])
def start_task(task_id: str, actor: str = Query("api")) -> dict:
    task = cpo.start_task(task_id, actor=actor)
    return {"task_id": task.uto_id, "status": task.status}


@app.post("/api/v1/tasks/{task_id}/mark-under-review", tags=["tasks"])
def mark_under_review(task_id: str, actor: str = Query("api")) -> dict:
    task = cpo.mark_under_review(task_id, actor=actor)
    return {"task_id": task.uto_id, "status": task.status}


@app.post("/api/v1/tasks/{task_id}/complete", tags=["tasks"])
@app.post("/api/tasks/{task_id}/complete", tags=["tasks"])
def complete_task(task_id: str, actor: str = Query("api")) -> dict:
    task = cpo.complete_task(task_id, actor=actor)
    return {"task_id": task.uto_id, "status": task.status}


@app.post("/api/v1/tasks/{task_id}/approve", tags=["tasks"])
@app.post("/api/tasks/{task_id}/approve", tags=["tasks"])
def approve_task(task_id: str, data: Optional[ApprovalIn] = None,
                 approver_name: str = Query(""), approver_role: str = Query("")) -> dict:
    payload = data or ApprovalIn()
    task = cpo.approve_task(
        task_id,
        actor=approver_name or payload.approver_name or "api",
        approver_name=approver_name or payload.approver_name or None,
        approver_role=approver_role or payload.approver_role or None,
        comments=payload.comments,
    )
    return {"task_id": task.uto_id, "status": task.status}


@app.post("/api/v1/tasks/{task_id}/reject", tags=["tasks"])
def reject_task(task_id: str, data: ReasonIn, actor: str = Query("api")) -> dict:
    task = cpo.reject_task(task_id, actor=actor, reason=data.reason)
    return {"task_id": task.uto_id, "status": task.status}


@app.post("/api/v1/tasks/{task_id}/rework", tags=["tasks"])
def rework_task(task_id: str, data: ReasonIn, actor: str = Query("api")) -> dict:
    task = cpo.rework_task(task_id, actor=actor, reason=data.reason)
    return {"task_id": task.uto_id, "status": task.status}


@app.get("/api/v1/tasks/{task_id}/gate", tags=["tasks"])
@app.get("/api/tasks/{task_id}/gate", tags=["tasks"])
def check_gate(task_id: str) -> dict:
    _require_task(task_id)
    result = cpo.check_gate(task_id)
    return {"task_id": task_id, **result.to_dict()}


@app.post("/api/v1/tasks/{task_id}/waiver", tags=["tasks"])
@app.post("/api/tasks/{task_id}/waiver", tags=["tasks"])
def apply_waiver(task_id: str, data: WaiverApply) -> dict:
    _require_task(task_id)
    waiver = cpo.apply_waiver(
        task_id,
        parameter=data.parameter,
        rationale=data.rationale,
        waived_by=data.waived_by,
        scope=data.scope,
    )
    return {"task_id": task_id, "waiver_applied": True,
            "waiver": waiver.model_dump(mode="json")}


# --------------------------------------------------------------------------- #
# Audit trail (§14) and registry exchange
# --------------------------------------------------------------------------- #
@app.get("/api/v1/audit", tags=["ops"])
def get_audit(entity_id: Optional[str] = Query(None)) -> dict:
    entries = cpo.get_audit_log(entity_id=entity_id)
    return {"entries": [e.model_dump(mode="json") for e in entries]}


@app.get("/api/v1/registry/export", tags=["ops"])
@app.get("/api/registry/export", tags=["ops"])
def export_registry() -> dict:
    return cpo.registry.to_dict()


@app.post("/api/v1/registry/import", tags=["ops"])
@app.post("/api/registry/import", tags=["ops"])
def import_registry(payload: dict = Body(...)) -> dict:
    import json as _json

    try:
        cpo.import_json(_json.dumps(payload))
    except ValidationError as exc:
        return error_response("VALIDATION_ERROR", f"Registry payload invalid: {exc}")
    return {"status": "imported", "projects": len(cpo.registry.list_projects())}


# --------------------------------------------------------------------------- #
# Static UI
# --------------------------------------------------------------------------- #
@app.get("/", include_in_schema=False)
def index() -> Any:
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content=error_body(
        "NOT_FOUND", "UI assets are not installed; see app/static/"))


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class _NotFound(Exception):
    """Entity does not exist (§25.1 NOT_FOUND)."""


@app.exception_handler(_NotFound)
async def _not_found(request: Request, exc: _NotFound):
    return error_response("NOT_FOUND", str(exc))
