"""TSD-001 §5.3 r.3 — Confidence accounting engine.

Walks an assembled ECP plus the originating SITE and tallies every evidence
record by its confidence level, producing the §5.2.13 CONFIDENCE summary.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from ..schemas import ECP, ConfidenceLevel, ConfidenceSummary, UncertaintyItem

#: Canonical, non-duplicated ECP sections walked for evidence.
#:
#: ``confidence_summary`` is deliberately excluded: it is the *output* of this
#: pass, and counting it would let a stale summary inflate itself on
#: re-assembly.
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
    "outputs",
]

_LEVEL_FIELDS = ("confidence_level", "evidence_level_required", "confidence_minimum_required")

#: Numeric position of each level, used for the weighted average.
_LEVEL_SCORE = {ConfidenceLevel.A: 5.0, ConfidenceLevel.B: 4.0, ConfidenceLevel.C: 3.0,
                ConfidenceLevel.D: 2.0, ConfidenceLevel.E: 1.0}
_SCORE_LEVEL = {v: k for k, v in _LEVEL_SCORE.items()}


def _normalise_level(value: Any) -> Optional[ConfidenceLevel]:
    """Coerce a raw value into a ConfidenceLevel, or None if unrecognised."""
    if isinstance(value, ConfidenceLevel):
        return value
    if isinstance(value, str):
        try:
            return ConfidenceLevel(value.strip().upper())
        except ValueError:
            return None
    return None


def _count_evidence_in_object(obj: Any, counts: dict[ConfidenceLevel, int],
                              seen: set[int]) -> None:
    """Recursively tally confidence levels found on ``obj``.

    Handles three shapes: pydantic models, mappings (the ``list[dict]`` fields
    such as ECP soil layers) and sequences. Objects are visited at most once so
    shared references cannot double-count.
    """
    if obj is None:
        return

    if isinstance(obj, (str, int, float, bool, bytes)):
        return

    marker = id(obj)
    if marker in seen:
        return
    seen.add(marker)

    if isinstance(obj, dict):
        for key in _LEVEL_FIELDS:
            level = _normalise_level(obj.get(key))
            if level is not None:
                counts[level] += 1
                break
        for value in obj.values():
            _count_evidence_in_object(value, counts, seen)
        return

    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            _count_evidence_in_object(item, counts, seen)
        return

    # Pydantic model (or any object exposing a confidence level).
    for key in _LEVEL_FIELDS:
        if hasattr(obj, key):
            level = _normalise_level(getattr(obj, key))
            if level is not None:
                counts[level] += 1
                break

    # ``model_fields`` is a class attribute; read it from the type to stay clear
    # of the Pydantic 2.11 instance-access deprecation.
    for name in type(obj).model_fields if hasattr(type(obj), "model_fields") else {}:
        _count_evidence_in_object(getattr(obj, name, None), counts, seen)


class EvidenceCounter:
    """Count parameters by confidence level in an ECP (and its source site)."""

    @staticmethod
    def count_by_level(ecp: ECP, site: Any = None) -> dict[ConfidenceLevel, int]:
        """Return ``{ConfidenceLevel: count}`` across the ECP and optional site.

        The ECP site-data section is a faithful copy of SITE content
        (IMPLEMENTATION_NOTES #6), so a site passed alongside the ECP is walked
        for its non-projected records only — its soil layers and hydrology
        evidence already appear in ``site_data``.
        """
        counts: dict[ConfidenceLevel, int] = {level: 0 for level in ConfidenceLevel}
        seen: set[int] = set()

        for section_name in ECP_EVIDENCE_SECTIONS:
            section = getattr(ecp, section_name, None)
            _count_evidence_in_object(section, counts, seen)

        if site is not None:
            _count_evidence_in_object(getattr(site, "hazards", None), counts, seen)
            _count_evidence_in_object(getattr(site, "climate", None), counts, seen)

        return counts

    @staticmethod
    def summarise(ecp: ECP, site: Any = None) -> ConfidenceSummary:
        """Build the §5.2.13 CONFIDENCE summary for an assembled ECP.

        The weighted average uses A=5 … E=1 and is rounded to the nearest
        canonical level, so an all-level-E packet reports ``E``.
        """
        counts = EvidenceCounter.count_by_level(ecp, site)
        total = sum(counts.values())

        if total:
            weighted = sum(_LEVEL_SCORE[level] * n for level, n in counts.items()) / total
            average = _SCORE_LEVEL[min(_SCORE_LEVEL, key=lambda s: abs(s - weighted))]
        else:
            # No evidence anywhere: the packet carries no verified information.
            average = ConfidenceLevel.E

        uncertainty_items = EvidenceCounter.collect_uncertainties(ecp, site, counts)

        return ConfidenceSummary(
            level_a_count=counts[ConfidenceLevel.A],
            level_b_count=counts[ConfidenceLevel.B],
            level_c_count=counts[ConfidenceLevel.C],
            level_d_count=counts[ConfidenceLevel.D],
            level_e_count=counts[ConfidenceLevel.E],
            average_confidence=average,
            uncertainty_items=uncertainty_items,
        )

    @staticmethod
    def collect_uncertainties(
        ecp: ECP,
        site: Any = None,
        counts: Optional[dict[ConfidenceLevel, int]] = None,
    ) -> list[UncertaintyItem]:
        """Turn level-E parameters and open data gaps into §12 uncertainty items."""
        counts = counts if counts is not None else EvidenceCounter.count_by_level(ecp, site)
        items: list[UncertaintyItem] = []

        e_count = counts[ConfidenceLevel.E]
        if e_count:
            items.append(UncertaintyItem(
                parameter="unverified_assumptions",
                description=f"{e_count} parameter(s) rest on unverified level-E evidence",
                impact="high",
                recommended_action="Commission the site investigation listed in data_gaps",
            ))

        gaps = list(getattr(ecp.site_data, "data_gaps", []) or [])
        for gap in gaps:
            items.append(UncertaintyItem(
                parameter=gap,
                description="Open site data gap",
                impact="medium",
                recommended_action="Close before detailed design",
            ))
        return items


#: Backwards-compatible alias for the previous private helper name.
_count_evidence_in_dict = _count_evidence_in_object

# Re-exported for callers that annotated against the old union.
EvidenceLike = Union[dict, list, str, int, float, bool, None]
