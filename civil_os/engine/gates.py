"""TSD-001 §7.3 — Confidence gate implementation.

The gate blocks tasks when their required confidence level is not met, or when
level-E parameters lack documented waivers (except for safety-critical params,
which are never waivable).
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Optional

from ..schemas import UTO, ConfidenceLevel, Waiver


class GateError(Exception):
    """Gate check failed."""


class GateResult:
    """Outcome of a §7.3 gate check.

    Supports attribute access (``result.can_proceed``) and the historical tuple
    unpacking ``can_proceed, issues = cpo.check_gate(...)`` so both the HTTP
    API and existing callers work against the same object.
    """

    __slots__ = ("can_proceed", "issues", "level", "message")

    def __init__(
        self,
        can_proceed: bool,
        issues: Optional[list[str]] = None,
        level: Optional[ConfidenceLevel] = None,
        message: str = "",
    ) -> None:
        self.can_proceed = can_proceed
        self.issues = list(issues or [])
        self.level = level
        self.message = message

    def __iter__(self) -> Iterator:
        return iter((self.can_proceed, self.issues))

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int):
        return (self.can_proceed, self.issues)[index]

    def __bool__(self) -> bool:
        return self.can_proceed

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"GateResult(can_proceed={self.can_proceed}, issues={self.issues!r})"

    def to_dict(self) -> dict:
        """JSON-ready form for the HTTP API (§24.1 ``check_gate``)."""
        return {
            "can_proceed": self.can_proceed,
            "level": self.level.value if self.level else None,
            "message": self.message,
            "issues": self.issues,
        }


class ConfidenceGate:
    """§7.3 gate rule enforcement."""

    @staticmethod
    def evaluate(uto: UTO) -> GateResult:
        """Evaluate the gate and return a rich :class:`GateResult`.

        Rules:
        1. A level-E assumption on a safety-critical task is a hard block that
           no waiver can clear.
        2. A level-E assumption on any other task requires a documented waiver
           naming that assumption.
        3. A task with no bound ECP cannot be gated.
        4. Everything else passes.
        """
        issues: list[str] = []

        if uto.ecp_ref is None:
            issues.append("Task has no Engineering Context Packet bound; assemble an ECP first")

        for assumption in uto.assumptions:
            if assumption.confidence_level != ConfidenceLevel.E:
                continue
            if uto.safety_critical:
                # Safety-critical: NO WAIVERS, hard block.
                issues.append(
                    "Safety-critical task cannot proceed with level-E assumption: "
                    f"{assumption.assumption_text}"
                )
            elif not any(w.parameter == assumption.assumption_text for w in uto.waivers):
                issues.append(
                    f"Level-E assumption requires waiver: {assumption.assumption_text}"
                )

        can_proceed = not issues
        if can_proceed:
            message = "Gate open: no unwaived level-E assumptions"
        elif uto.safety_critical:
            message = "Gate blocked: safety-critical task has unwaivable level-E assumptions"
        else:
            message = f"Gate blocked: {len(issues)} issue(s) require action"

        return GateResult(can_proceed=can_proceed, issues=issues, message=message)

    @staticmethod
    def check_uto(uto: UTO) -> GateResult:
        """Check if a UTO can proceed (gate open = True, closed = False)."""
        return ConfidenceGate.evaluate(uto)

    @staticmethod
    def apply_waiver(uto: UTO, waiver: Waiver) -> None:
        """Apply a waiver to a UTO (idempotent)."""
        if not any(w.parameter == waiver.parameter for w in uto.waivers):
            uto.waivers.append(waiver)
