"""CIVIL-OS engine — ECP assembly, validation, versioning, gates."""
from .assembler import AssemblyError, ECPAssembler
from .evidence import EvidenceCounter
from .gates import ConfidenceGate, GateError
from .jurisdiction import JurisdictionResolver
from .requirements_matrix import RequirementsMatrix
from .validator import ECPValidator, ValidationError
from .versioning import ECPVersionManager


__all__ = [
    "ECPAssembler", "AssemblyError",
    "ECPValidator", "ValidationError",
    "ECPVersionManager",
    "ConfidenceGate", "GateError",
    "JurisdictionResolver",
    "RequirementsMatrix",
    "EvidenceCounter",
]
