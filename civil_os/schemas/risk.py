"""TSD-001 §4.2.7 — RISK entity."""
from __future__ import annotations


from typing import Literal, Optional


from pydantic import Field


from .base import CivilOSModel, ConfidenceLevel, Severity, new_id




class Risk(CivilOSModel):
    """TSD-001 §4.2.7 — RISK."""


    risk_id: str = Field(default_factory=new_id)
    project_id: str
    risk_type: Literal["technical", "schedule", "cost", "organizational", "environmental", "safety"]
    hazard_description: str = Field(..., min_length=1)
    potential_impact: str = ""
    probability: Literal["negligible", "low", "medium", "high", "certain"] = "low"
    consequence: Literal["insignificant", "minor", "moderate", "major", "catastrophic"] = "minor"
    risk_level: Literal["low", "medium", "high", "extreme"] = "low"
    mitigation_strategy: str = ""
    responsible_party: str = ""
    target_residual_risk: str = "low"
    contingency_plan: str = ""
    early_warning_indicators: list[str] = Field(default_factory=list)
    review_frequency_days: int = Field(30, ge=1)
    confidence_level: ConfidenceLevel = ConfidenceLevel.C
    severity: Severity = Severity.major
