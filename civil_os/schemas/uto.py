"""TSD-001 §6 — UTO (Universal Task Object) entity and lifecycle state machine."""
from __future__ import annotations


from datetime import datetime
from typing import Literal, Optional


from pydantic import Field


from .base import CivilOSModel, ConfidenceLevel, UncertaintyItem, Waiver, new_id, utcnow




class TaskStatus(str):
    """§6.3 UTO lifecycle states."""
    READY = "ready"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    COMPLETED = "completed"




class TaskDependency(CivilOSModel):
    task_id: str
    task_name: str = ""
    dependency_type: Literal["blocks", "informs", "requires"] = "blocks"
    lag_days: int = Field(0, ge=0)




class TaskConstraint(CivilOSModel):
    constraint_type: str
    description: str
    severity: Literal["low", "medium", "high"] = "medium"




class TaskInput(CivilOSModel):
    input_name: str
    source: str
    format: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.C




class TaskRequirementRef(CivilOSModel):
    requirement_id: str
    discipline: str
    satisfaction_method: Literal["design", "analysis", "test", "inspection"] = "analysis"




class StandardRef(CivilOSModel):
    standard_name: str
    section_reference: str = ""
    requirement: str = ""




class AssumptionItem(CivilOSModel):
    assumption_text: str
    confidence_level: ConfidenceLevel = ConfidenceLevel.E
    validation_plan: str = ""
    risk_if_false: str = ""




class CalculationRequirement(CivilOSModel):
    calculation_type: str
    description: str = ""
    inputs_required: list[str] = Field(default_factory=list)
    accuracy_tolerance: str = ""




class ECPRef(CivilOSModel):
    """Reference to a specific ECP and version consumed by this task."""
    ecp_id: str
    version: int
    sections_used: list[str] = Field(default_factory=list)
    confidence_minimum_required: ConfidenceLevel = ConfidenceLevel.D




class TaskResults(CivilOSModel):
    result_name: str
    result_type: str
    description: str = ""
    format: str = ""
    storage_location: str = ""




class ExecutionLogEntry(CivilOSModel):
    timestamp: datetime = Field(default_factory=utcnow)
    event_type: str
    actor: str = ""
    description: str = ""
    details: dict = Field(default_factory=dict)




class ApprovalStep(CivilOSModel):
    discipline: str
    approver_role: str
    required: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: str = ""




class UTO(CivilOSModel):
    """TSD-001 §6 — Universal Task Object (UTO).

    Represents a discrete engineering task with:
    - Full context from ECP (§5)
    - Lifecycle state machine (§6.3)
    - Confidence & evidence tracking (§7)
    - Waiver capability (§7.3) for non-safety-critical parameters only
    """


    uto_id: str = Field(default_factory=new_id)
    project_id: str
    ecp_ref: ECPRef  # which ECP version this task consumes
    task_name: str = Field(..., min_length=1)
    description: str = ""
    discipline: str
    task_type: Literal["design", "analysis", "investigation", "review", "coordination"]
    phase: str = ""
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    safety_critical: bool = False  # Phase-1 extension


    # Inputs & requirements
    dependencies: list[TaskDependency] = Field(default_factory=list)
    inputs: list[TaskInput] = Field(default_factory=list)
    requirements_satisfied: list[TaskRequirementRef] = Field(default_factory=list)
    applicable_standards: list[StandardRef] = Field(default_factory=list)
    assumptions: list[AssumptionItem] = Field(default_factory=list)
    constraints: list[TaskConstraint] = Field(default_factory=list)


    # Calculations & analysis
    calculations_required: list[CalculationRequirement] = Field(default_factory=list)


    # Results & outputs
    expected_results: list[TaskResults] = Field(default_factory=list)


    # Lifecycle (§6.3)
    status: str = TaskStatus.READY
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_days: int = Field(5, ge=1)
    assigned_to: str = ""


    # Review & approval
    requires_review: bool = False
    review_required_from: list[str] = Field(default_factory=list)
    approval_chain: list[ApprovalStep] = Field(default_factory=list)


    # Confidence & evidence (§7)
    evidence_level_required: ConfidenceLevel = ConfidenceLevel.B
    uncertainties: list[UncertaintyItem] = Field(default_factory=list)
    waivers: list[Waiver] = Field(default_factory=list)


    # Audit trail
    execution_log: list[ExecutionLogEntry] = Field(default_factory=list)


    notes: str = ""
    tags: list[str] = Field(default_factory=list)
