"""TSD-001 §7.3 — Confidence gate implementation.

The gate blocks tasks when their required confidence level is not met,
or when level-E parameters lack documented waivers (except for safety-critical params).
"""
from __future__ import annotations


from typing import TYPE_CHECKING


from ..schemas import ConfidenceLevel, UTO, Waiver


if TYPE_CHECKING:
    pass




class GateError(Exception):
    """Gate check failed."""
    pass




class ConfidenceGate:
    """§7.3 gate rule enforcement."""


    @staticmethod
    def check_uto(uto: UTO) -> tuple[bool, list[str]]:
        """
        Check if a UTO can proceed (gate is OPEN = True, CLOSED = False).
        Returns (can_proceed, list_of_issues).

        Rule:
        1. If any assumption is level-E and safety_critical=True, block (no waivers).
        2. If any assumption is level-E, require a waiver to proceed (non-safety-critical).
        3. All other levels pass through.
        """
        issues = []


        for assumption in uto.assumptions:
            if assumption.confidence_level == ConfidenceLevel.E:
                # Level-E parameter
                if uto.safety_critical:
                    # Safety-critical: NO WAIVERS, hard block
                    issues.append(
                        f"Safety-critical task cannot proceed with "
                        f"level-E assumption: {assumption.assumption_text}"
                    )
                else:
                    # Non-safety-critical: require waiver
                    waived = any(
                        w.parameter == assumption.assumption_text
                        for w in uto.waivers
                    )
                    if not waived:
                        issues.append(
                            f"Level-E assumption requires waiver: {assumption.assumption_text}"
                        )


        can_proceed = len(issues) == 0
        return can_proceed, issues


    @staticmethod
    def apply_waiver(uto: UTO, waiver: Waiver) -> None:
        """Apply a waiver to a UTO (idempotent)."""
        existing = [w for w in uto.waivers if w.parameter == waiver.parameter]
        if not existing:
            uto.waivers.append(waiver)
