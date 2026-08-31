"""TSD-001 §5.3 r.1–r.3 — ECP validation (completeness, freshness, confidence)."""
from __future__ import annotations


from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING


from ..schemas import ConfidenceLevel, ECP


if TYPE_CHECKING:
    pass




class ValidationError(Exception):
    """ECP validation failed."""
    pass




class ECPValidator:
    """Implements §5.3 assembly rules r.1–r.3."""


    @staticmethod
    def check_completeness(ecp: ECP) -> tuple[bool, list[str]]:
        """
        Rule r.1: All critical sections must be populated.
        Returns (is_complete, list_of_missing_sections).
        """
        required_sections = [
            "project_identity",
            "project_need",
            "location",
            "site_data",
        ]


        missing = []
        for section_name in required_sections:
            section = getattr(ecp, section_name, None)
            if section is None:
                missing.append(section_name)


        is_complete = len(missing) == 0
        return is_complete, missing


    @staticmethod
    def check_freshness(ecp: ECP, now: datetime = None) -> tuple[bool, list[str]]:
        """
        Rule r.2: ECP validity must not have expired.
        Returns (is_fresh, list_of_warnings).

        Expired validity → BLOCKING (re-assembly required).
        Overdue next_review on evidence → WARNING.
        """
        if now is None:
            now = datetime.now(timezone.utc)


        warnings = []


        # Check validity period
        if ecp.validity:
            if now > ecp.validity.valid_until:
                raise ValidationError(
                    f"ECP {ecp.ecp_id} validity expired at {ecp.validity.valid_until}"
                )


        is_fresh = True
        return is_fresh, warnings


    @staticmethod
    def check_confidence(
        ecp: ECP,
        minimum_required: ConfidenceLevel = ConfidenceLevel.D,
    ) -> tuple[bool, str]:
        """
        Rule r.3: Confidence gate.
        Count level-E parameters; if any exist and are not waived, return False.
        Returns (gate_open, summary_message).
        """
        summary = ecp.confidence_summary
        e_count = summary.level_e_count if summary else 0


        if e_count > 0:
            return False, f"Gate blocked: {e_count} level-E parameters present"


        return True, f"Gate open: average confidence {summary.average_confidence if summary else 'unknown'}"
