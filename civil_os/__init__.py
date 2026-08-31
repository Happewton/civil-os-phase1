"""CIVIL-OS — Civil Engineering Project Intelligence & Execution System.


Phase 1 prototype: Project Context Engine (core schemas, ECP assembler,
basic CPO). Implements TSD-001 v0.1 (draft, 2026-08-31).
"""
__version__ = "0.1.0"


from .schemas import (ConfidenceLevel, ECP, Need, ParameterEvidence, Project,
                      Requirement, Site, UTO)
from .engine import (ECPAssembler, ECPValidator, ECPVersionManager,
                     JurisdictionResolver)
from .cpo import CivilProjectOrchestrator, ProjectRegistry


__all__ = [
    "CivilProjectOrchestrator", "ProjectRegistry", "ECPAssembler",
    "ECPValidator", "ECPVersionManager", "JurisdictionResolver",
    "Project", "Site", "Need", "Requirement", "ECP", "UTO",
    "ConfidenceLevel", "ParameterEvidence", "__version__",
]
