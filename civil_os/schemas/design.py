"""TSD-001 §4.2.5 DESIGN_MODEL and §4.2.6 CALCULATION entities."""
from __future__ import annotations


from datetime import datetime
from typing import Any, Literal, Optional


from pydantic import Field


from .base import CivilOSModel, ConfidenceLevel, new_id, utcnow




class ModelInput(CivilOSModel):
    parameter: str
    value: Any
    unit: str = ""
    source: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.E




class AnalysisResult(CivilOSModel):
    analysis_type: str
    result_summary: str = ""
    governing_case: str = ""
    safety_factors: dict = Field(default_factory=dict)
    output_files: list[str] = Field(default_factory=list)




class DesignModel(CivilOSModel):
    """TSD-001 §4.2.5 — DESIGN_MODEL."""


    model_id: str = Field(default_factory=new_id)
    project_id: str
    discipline: str
    model_type: str
    description: str = ""
    software_tool: str = ""
    model_version: str = ""
    inputs: list[ModelInput] = Field(default_factory=list)
    results: list[AnalysisResult] = Field(default_factory=list)
    validation_status: Literal["unvalidated", "validated", "benchmarked"] = "unvalidated"
    created_at: datetime = Field(default_factory=utcnow)




class CalculationInput(CivilOSModel):
    parameter: str
    value: Any
    unit: str = ""
    source_model_id: Optional[str] = None
    confidence_level: ConfidenceLevel = ConfidenceLevel.E




class Calculation(CivilOSModel):
    """TSD-001 §4.2.6 — CALCULATION."""


    calculation_id: str = Field(default_factory=new_id)
    project_id: str
    discipline: str
    calculation_type: str
    description: str = ""
    inputs: list[CalculationInput] = Field(default_factory=list)
    output_value: Any = None
    output_unit: str = ""
    method: str = ""
    assumptions: list[str] = Field(default_factory=list)
    code_reference: str = ""
    design_life_phase: str = ""
    status: Literal["preliminary", "final", "superseded"] = "preliminary"
    performed_by: str = ""
    reviewed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
