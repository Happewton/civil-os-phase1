"""CIVIL-OS — Civil Engineering Project Intelligence & Execution System.


Phase 1 prototype: Project Context Engine (core schemas, ECP assembler,
basic CPO). Implements TSD-001 v0.1 (draft, 2026-08-31).
"""
__version__ = "0.2.0"


from .cpo import CivilProjectOrchestrator, ProjectRegistry
from .engine import ECPAssembler, ECPValidator, ECPVersionManager, JurisdictionResolver
from .schemas import ECP, UTO, ConfidenceLevel, Need, ParameterEvidence, Project, Requirement, Site

__all__ = [
    "CivilProjectOrchestrator", "ProjectRegistry", "ECPAssembler",
    "ECPValidator", "ECPVersionManager", "JurisdictionResolver",
    "Project", "Site", "Need", "Requirement", "ECP", "UTO",
    "ConfidenceLevel", "ParameterEvidence", "__version__",
]
