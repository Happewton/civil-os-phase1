"""CIVIL-OS base schema types.


Covers TSD-001 §4 foundations and §7 (Confidence & Evidence Classification
System). All entities carry UUID4 ids, timezone-aware UTC ISO-8601
timestamps, reject unknown fields (no silent data), and re-validate on
attribute assignment.
"""
from __future__ import annotations


import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional


from pydantic import BaseModel, ConfigDict, Field




def utcnow() -> datetime:
    """Timezone-aware UTC timestamp (all CIVIL-OS timestamps are UTC)."""
    return datetime.now(timezone.utc)




def new_id() -> str:
    """UUID4 string — the standard CIVIL-OS entity identifier."""
    return str(uuid.uuid4())




# --------------------------------------------------------------------------- #
# §7.1 Confidence levels
# --------------------------------------------------------------------------- #


class ConfidenceLevel(str, Enum):
    """Confidence & Evidence Classification System (TSD-001 §7.1)."""


    A = "A"  # Measured / Verified on this project
    B = "B"  # Authoritative external source
    C = "C"  # Interpolated / Modeled
    D = "D"  # Engineering Correlation
    E = "E"  # Unverified Assumption




#: MCP-side confidence labels (§8.4) mapped onto the canonical A–E scale.
MCP_CONFIDENCE_MAP = {
    "MEASURED": ConfidenceLevel.A,
    "INTERPOLATED": ConfidenceLevel.C,
    "CORRELATED": ConfidenceLevel.D,
    "ASSUMED": ConfidenceLevel.E,
    "ENGINEERING_JUDGMENT": ConfidenceLevel.D,
}




class EvidenceStatus(str, Enum):
    verified = "verified"
    provisional = "provisional"
    must_be_verified = "must_be_verified"
    superseded = "superseded"




# --------------------------------------------------------------------------- #
# Lifecycle / project enums
# --------------------------------------------------------------------------- #


class LifecyclePhase(str, Enum):
    need_assessment = "need_assessment"
    feasibility = "feasibility"
    concept_design = "concept_design"
    preliminary_design = "preliminary_design"
    detailed_design = "detailed_design"
    procurement = "procurement"
    construction = "construction"
    commissioning = "commissioning"
    operation = "operation"
    decommissioning = "decommissioning"




class ProjectStatus(str, Enum):
    draft = "draft"
    active = "active"
    on_hold = "on_hold"
    completed = "completed"
    archived = "archived"




class ProjectType(str, Enum):
    transportation = "transportation"
    water = "water"
    water_supply = "water_supply"
    wastewater = "wastewater"
    structural = "structural"
    environmental = "environmental"
    energy = "energy"
    urban = "urban"
    mining = "mining"
    building = "building"




class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"




class Severity(str, Enum):
    blocking = "blocking"
    major = "major"
    minor = "minor"
    informational = "informational"




# --------------------------------------------------------------------------- #
# Base model & §7.2 Parameter Evidence Record
# --------------------------------------------------------------------------- #


class CivilOSModel(BaseModel):
    """Common configuration for every CIVIL-OS entity."""


    model_config = ConfigDict(
        extra="forbid",          # no silent / unknown data
        use_enum_values=True,    # serialize enums as their values
        validate_assignment=True,
    )




class Uncertainty(CivilOSModel):
    type: str = "range"
    value: float
    unit: Optional[str] = None




class ApplicableRange(CivilOSModel):
    min: float
    max: float
    unit: Optional[str] = None




class ParameterEvidence(CivilOSModel):
    """TSD-001 §7.2 — every parameter carries value + provenance + confidence."""


    parameter: str = Field(..., description="e.g. 'groundwater_level'")
    value: Any
    unit: Optional[str] = None
    source: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.E
    status: EvidenceStatus = EvidenceStatus.must_be_verified
    method: Optional[str] = None
    uncertainty: Optional[Uncertainty] = None
    applicable_range: Optional[ApplicableRange] = None
    last_verified: Optional[datetime] = None
    verified_by: Optional[str] = None
    next_review: Optional[datetime] = None
    notes: Optional[str] = None




class UncertaintyItem(CivilOSModel):
    """Uncertainty entry shared by the ECP (§5.2 §12) and UTO (§6.2)."""
    parameter: str
    description: str = ""
    impact: Literal["low", "medium", "high"] = "medium"
    recommended_action: str = ""




class Waiver(CivilOSModel):
    """§7.3 — documented waiver for a level-E parameter.


    Phase-1 waivers are task-scoped and are NEVER accepted for
    safety-critical parameters.
    """
    parameter: str
    rationale: str = Field(..., min_length=10)
    waived_by: str
    waived_at: datetime = Field(default_factory=utcnow)
    scope: Literal["task", "project"] = "task"




# --------------------------------------------------------------------------- #
# Deterministic hazard/risk derivation (documented heuristic)
# --------------------------------------------------------------------------- #


_PROBABILITY_ORDER = ("negligible", "low", "medium", "high", "certain")
_CONSEQUENCE_ORDER = ("insignificant", "minor", "moderate", "major", "catastrophic")




def derive_risk_level(probability: str, consequence: str) -> str:
    """5x5 probability x consequence matrix (see IMPLEMENTATION_NOTES.md #9)."""
    try:
        p = _PROBABILITY_ORDER.index(probability) + 1
        c = _CONSEQUENCE_ORDER.index(consequence) + 1
    except ValueError:
        return "medium"  # default fallback
    score = p * c  # 1..25
    if score <= 4:
        return "low"
    if score <= 9:
        return "medium"
    if score <= 16:
        return "high"
    return "extreme"
