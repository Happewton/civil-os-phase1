"""TSD-001 §5.2 — ECP (Engineering Context Packet) entity."""
from __future__ import annotations


from datetime import datetime
from typing import Any, Optional


from pydantic import Field


from .base import CivilOSModel, ConfidenceLevel, ParameterEvidence, UncertaintyItem, new_id, utcnow




class ValidityPeriod(CivilOSModel):
    valid_from: datetime
    valid_until: datetime
    rationale: str = ""




class ECPProjectIdentity(CivilOSModel):
    """§5.2.1 — PROJECT IDENTITY section."""
    project_id: str
    name: str
    description: str = ""
    project_type: str
    design_life_years: int
    current_phase: str
    created_at: datetime




class ECPProjectNeed(CivilOSModel):
    """§5.2.2 — PROJECT NEED section."""
    need_id: str
    category: str
    problem_statement: str
    affected_population: int = 0
    performance_targets: list[str] = Field(default_factory=list)




class ECPStakeholderRequirements(CivilOSModel):
    """§5.2.3 — STAKEHOLDER REQUIREMENTS section."""
    stakeholder_name: str
    role: str
    interests: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    approval_required: bool = False




class ECPLocation(CivilOSModel):
    """§5.2.4 — LOCATION section."""
    country: str
    region: str = ""
    municipality: str = ""
    latitude: float
    longitude: float
    elevation_m: float = 0.0




class ECPSiteData(CivilOSModel):
    """§5.2.5 — SITE DATA section (duplicates §4.2.4 content per design decision #6)."""
    soil_layers: list[dict] = Field(default_factory=list)
    hydrology_summary: dict = Field(default_factory=dict)
    hazards_summary: list[dict] = Field(default_factory=list)
    existing_assets: list[dict] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)




class BudgetConstraint(CivilOSModel):
    """§5.2.6 — BUDGET section."""
    total_budget: float
    currency: str = "USD"
    allocated_by_phase: dict = Field(default_factory=dict)
    contingency_percent: float = 10.0




class ScheduleConstraint(CivilOSModel):
    """§5.2.7 — SCHEDULE section."""
    target_start: datetime
    target_completion: datetime
    critical_dates: list[dict] = Field(default_factory=list)




class LandConstraint(CivilOSModel):
    """§5.2.8 — LAND section."""
    available_area_m2: float
    land_use_constraints: list[str] = Field(default_factory=list)
    ownership_status: str = ""




class ApplicableCode(CivilOSModel):
    """§5.2.9 — CODES section."""
    jurisdiction: str
    code_name: str
    section_reference: str = ""
    applicability: str = ""




class ECPConstraints(CivilOSModel):
    """§5.2.10 — CONSTRAINTS section."""
    constraints: list[str] = Field(default_factory=list)
    risk_tolerance: str = "moderate"




class DesignLife(CivilOSModel):
    """§5.2.11 — DESIGN LIFE section."""
    design_life_years: int
    service_phases: list[str] = Field(default_factory=list)
    end_of_life_strategy: str = ""




class ECPClimateData(CivilOSModel):
    """§5.2.12 — CLIMATE section."""
    temperature_range: Optional[dict] = None
    rainfall_statistics: Optional[dict] = None
    wind_regime: Optional[dict] = None
    seismic_zone: str = ""




class ConfidenceSummary(CivilOSModel):
    """§5.2.13 — CONFIDENCE summary."""
    level_a_count: int = 0
    level_b_count: int = 0
    level_c_count: int = 0
    level_d_count: int = 0
    level_e_count: int = 0
    average_confidence: str = "C"
    uncertainty_items: list[UncertaintyItem] = Field(default_factory=list)




class RequiredOutput(CivilOSModel):
    """§5.2.14 — OUTPUTS section."""
    output_name: str
    discipline: str
    format: str = ""
    deadline: Optional[datetime] = None
    responsible_party: str = ""




class ECP(CivilOSModel):
    """TSD-001 §5.2 — Engineering Context Packet (14 sections + identity)."""


    ecp_id: str = Field(default_factory=new_id)
    project_id: str
    version: int = Field(1, ge=1)
    content_hash: str = ""  # SHA256 of canonical JSON for idempotency
    created_at: datetime = Field(default_factory=utcnow)
    validity: ValidityPeriod = Field(...)


    # 14 sections + identity
    project_identity: ECPProjectIdentity
    project_need: ECPProjectNeed
    stakeholder_requirements: list[ECPStakeholderRequirements] = Field(default_factory=list)
    location: ECPLocation
    site_data: ECPSiteData
    budget: Optional[BudgetConstraint] = None
    schedule: Optional[ScheduleConstraint] = None
    land: Optional[LandConstraint] = None
    applicable_codes: list[ApplicableCode] = Field(default_factory=list)
    constraints: Optional[ECPConstraints] = None
    design_life: Optional[DesignLife] = None
    climate: Optional[ECPClimateData] = None
    confidence_summary: ConfidenceSummary = Field(default_factory=ConfidenceSummary)
    outputs: list[RequiredOutput] = Field(default_factory=list)
    assembled_by: str = ""
    notes: str = ""
