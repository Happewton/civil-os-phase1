"""TSD-001 §5.3 r.3 — Confidence accounting engine.

Walks the ECP and counts evidence by confidence level.
"""
from __future__ import annotations


from typing import TYPE_CHECKING


from ..schemas import ConfidenceLevel, ECP


if TYPE_CHECKING:
    pass




# Sections of the ECP that carry evidence (canonical, non-duplicated)
ECP_EVIDENCE_SECTIONS = [
    "project_identity",
    "project_need",
    "stakeholder_requirements",
    "location",
    "site_data",
    "budget",
    "schedule",
    "land",
    "applicable_codes",
    "constraints",
    "design_life",
    "climate",
    "confidence_summary",
    "outputs",
]




class EvidenceCounter:
    """Count parameters by confidence level in an ECP."""


    @staticmethod
    def count_by_level(ecp: ECP) -> dict[str, int]:
        """
        Iterate over ECP evidence sections and count parameters by confidence level.
        Returns a dict: { "A": count, "B": count, ..., "E": count }
        """
        counts = {
            ConfidenceLevel.A: 0,
            ConfidenceLevel.B: 0,
            ConfidenceLevel.C: 0,
            ConfidenceLevel.D: 0,
            ConfidenceLevel.E: 0,
        }


        # Walk each canonical section
        for section_name in ECP_EVIDENCE_SECTIONS:
            section = getattr(ecp, section_name, None)
            if section is None:
                continue


            # Count evidence in each section
            if isinstance(section, list):
                for item in section:
                    _count_evidence_in_object(item, counts)
            else:
                _count_evidence_in_object(section, counts)


        return counts




def _count_evidence_in_object(obj: any, counts: dict) -> None:
    """Recursively count ParameterEvidence objects in an object."""
    if obj is None:
        return


    if hasattr(obj, "confidence_level"):
        # Direct ParameterEvidence or similar
        level = getattr(obj, "confidence_level", None)
        if level:
            counts[level] = counts.get(level, 0) + 1


    # Recurse into nested objects
    if hasattr(obj, "model_dump"):
        # Pydantic model
        for k, v in obj.model_dump(exclude_none=True).items():
            if isinstance(v, list):
                for item in v:
                    _count_evidence_in_object(item, counts)
            elif isinstance(v, dict):
                for item_v in v.values():
                    _count_evidence_in_object(item_v, counts)
            else:
                _count_evidence_in_object(v, counts)
