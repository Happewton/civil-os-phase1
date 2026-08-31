"""TSD-001 §4.2.3 — REQUIREMENT entity."""
from __future__ import annotations


from datetime import datetime
from enum import Enum
from typing import Literal, Optional


from pydantic import Field


from .base import CivilOSModel, ConfidenceLevel, new_id, utcnow




class RequirementStatus(str, Enum):
    draft = "draft"
    reviewed = "reviewed"
    approved = "approved"
    verified = "verified"
    changed = "changed"
    rejected = "rejected"




class TraceabilityLink(CivilOSModel):
    element_type: str
    element_id: str




class RequirementChange(CivilOSModel):
    version: int = Field(..., ge=1)
    changed_at: datetime = Field(default_factory=utcnow)
    changed_by: str
    reason: str
    old_value: str
    new_value: str




class Requirement(CivilOSModel):
    """TSD-001 §4.2.3 — REQUIREMENT."""


    requirement_id: str = Field(default_factory=new_id)
    project_id: str
    parent_requirement_id: Optional[str] = None
    discipline: str
    category: Literal["functional", "performance", "constraint", "interface", "safety"]
    description: str = Field(..., min_length=1)
    priority: Literal["mandatory", "desirable", "optional"] = "desirable"
    verification_method: Literal["inspection", "test", "analysis", "demonstration"] = "analysis"
    acceptance_criteria: str = ""
    allocated_to: str = ""
    status: RequirementStatus = RequirementStatus.draft
    traceability: list[TraceabilityLink] = Field(default_factory=list)
    change_history: list[RequirementChange] = Field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.B
