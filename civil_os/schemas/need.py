"""TSD-001 §4.2.2 — NEED entity."""
from __future__ import annotations


from datetime import datetime
from typing import Literal, Optional


from pydantic import Field


from .base import CivilOSModel, ConfidenceLevel, Severity, new_id, utcnow




class AffectedPopulation(CivilOSModel):
    count: int = Field(0, ge=0)
    description: str = ""
    vulnerable_groups: list[str] = Field(default_factory=list)




class PerformanceTarget(CivilOSModel):
    metric: str
    target_value: str
    unit: str = ""
    deadline: Optional[datetime] = None




class NeedConstraint(CivilOSModel):
    type: Literal["land", "political", "institutional", "financial", "technical"]
    description: str
    severity: Severity = Severity.minor




class Need(CivilOSModel):
    """TSD-001 §4.2.2 — NEED."""


    need_id: str = Field(default_factory=new_id)
    project_id: str
    category: Literal["social", "economic", "environmental", "safety", "infrastructure"]
    problem_statement: str = Field(..., min_length=1)
    affected_population: AffectedPopulation = Field(default_factory=AffectedPopulation)
    service_gap: str = ""
    current_demand: str = ""
    future_demand: str = ""
    performance_targets: list[PerformanceTarget] = Field(default_factory=list)
    social_objectives: list[str] = Field(default_factory=list)
    economic_objectives: list[str] = Field(default_factory=list)
    environmental_objectives: list[str] = Field(default_factory=list)
    resilience_objectives: list[str] = Field(default_factory=list)
    constraints: list[NeedConstraint] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    recommended_investigations: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.B
    created_at: datetime = Field(default_factory=utcnow)
