"""TSD-001 §4.2.1 — PROJECT entity."""
from __future__ import annotations


from datetime import datetime
from typing import Literal, Optional


from pydantic import Field, field_validator, model_validator


from .base import (CivilOSModel, LifecyclePhase, Priority, ProjectStatus,
                   ProjectType, new_id, utcnow)




class CoordinateSystem(CivilOSModel):
    epsg_code: int = Field(..., gt=0)
    name: str
    datum: str




class Location(CivilOSModel):
    """Project location — the anchor of the §5.3 jurisdiction cascade."""


    country: str = Field(..., min_length=2, max_length=2,
                         description="ISO 3166-1 alpha-2 country code")
    region: str = ""
    municipality: str = ""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation_m: float = 0.0


    @field_validator("country")
    @classmethod
    def _normalize_country(cls, value: str) -> str:
        return value.strip().upper()




class Stakeholder(CivilOSModel):
    role: str
    organization: str = ""
    contact: str = ""
    interests: list[str] = Field(default_factory=list)
    influence: Literal["low", "medium", "high"] = "medium"




class ApprovalChainEntry(CivilOSModel):
    discipline: str = "all"
    approver_role: str
    threshold: Optional[str] = None




class PhaseHistoryEntry(CivilOSModel):
    phase: LifecyclePhase
    entered_at: datetime = Field(default_factory=utcnow)
    exited_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    reason: str = ""




class Project(CivilOSModel):
    """TSD-001 §4.2.1 — PROJECT."""


    project_id: str = Field(default_factory=new_id)
    name: str = Field(..., min_length=1)
    status: ProjectStatus = ProjectStatus.draft
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


    description: str = ""
    project_type: ProjectType
    design_life_years: int = Field(50, ge=1, le=200)
    jurisdiction: str = ""
    coordinate_system: Optional[CoordinateSystem] = None
    vertical_datum: str = ""


    current_phase: LifecyclePhase = LifecyclePhase.need_assessment
    phase_history: list[PhaseHistoryEntry] = Field(default_factory=list)


    project_sponsor: str = ""
    stakeholders: list[Stakeholder] = Field(default_factory=list)
    approval_chain: list[ApprovalChainEntry] = Field(default_factory=list)


    tags: list[str] = Field(default_factory=list)
    priority: Priority = Priority.medium
    budget_currency: str = "USD"


    # -- Phase-1 pragmatic extensions (see IMPLEMENTATION_NOTES.md #2) -------
    location: Optional[Location] = None
    budget_amount: Optional[float] = Field(None, ge=0)
    target_completion: Optional[datetime] = None
    land_area_available_m2: Optional[float] = Field(None, ge=0)
    risk_tolerance: Literal["conservative", "moderate", "aggressive"] = "moderate"


    @model_validator(mode="before")
    @classmethod
    def _seed_phase_history(cls, data):
        if isinstance(data, dict) and not data.get("phase_history"):
            data = dict(data)
            data["phase_history"] = [{
                "phase": data.get("current_phase", "need_assessment"),
                "reason": "Project created",
            }]
        return data


    def touch(self) -> None:
        self.updated_at = utcnow()
