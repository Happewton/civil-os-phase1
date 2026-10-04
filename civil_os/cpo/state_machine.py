"""TSD-001 §6.3 — UTO lifecycle state machine."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from ..schemas import ALL_TASK_STATES, UTO, ExecutionLogEntry, TaskStatus


class StateMachineError(Exception):
    """State transition invalid."""


class GateBlocked(StateMachineError):
    """The §7.3 confidence gate blocked a transition.

    Carries the individual blocking issues so the HTTP layer can return them
    as a 403 ``GATE_BLOCKED`` body.
    """

    def __init__(self, message: str, issues: Optional[list[str]] = None) -> None:
        super().__init__(message)
        self.issues = list(issues or [])


class UTOStateMachine:
    """§6.3 — UTO lifecycle state machine.

    States: ready → in_progress → under_review → approved → completed
            blocked (parked on an unmet prerequisite)

    Transitions:
    - ready → in_progress (start_task)
    - in_progress → under_review (mark_under_review; → approved when no review)
    - under_review → approved (approve_task)
    - under_review → ready (reject_task, reason recorded)
    - approved → completed (complete_task)
    - approved → in_progress (rework_task)
    - ready → blocked / blocked → ready (park and release)
    - any → any (revert_state, for correction, with reason)
    """

    @staticmethod
    def start_task(uto: UTO, actor: str = "system") -> None:
        """Transition ready → in_progress.

        A task parked in ``blocked`` may also be started: that is the normal
        release path once the confidence gate opens or a dependency clears.
        """
        if uto.status not in (TaskStatus.READY, TaskStatus.BLOCKED):
            raise StateMachineError(
                f"Cannot start task in state {uto.status}; expected READY or BLOCKED"
            )
        UTOStateMachine.log_event(
            uto, "start_task", actor,
            "Task started" if uto.status == TaskStatus.READY else "Task started (released from blocked)",
        )
        uto.status = TaskStatus.IN_PROGRESS

    @staticmethod
    def mark_under_review(uto: UTO, actor: str = "system") -> None:
        """Transition in_progress → under_review (or → approved if no review)."""
        if uto.status != TaskStatus.IN_PROGRESS:
            raise StateMachineError(
                f"Cannot mark under review from state {uto.status}; expected IN_PROGRESS"
            )

        if uto.requires_review:
            uto.status = TaskStatus.UNDER_REVIEW
            UTOStateMachine.log_event(uto, "mark_under_review", actor,
                                      "Task marked for review")
        else:
            # Auto-approve if no review required.
            uto.status = TaskStatus.APPROVED
            UTOStateMachine.log_event(uto, "auto_approve", actor,
                                      "Task approved (no review required)")

    @staticmethod
    def approve_task(uto: UTO, actor: str = "system") -> None:
        """Transition under_review → approved."""
        if uto.status != TaskStatus.UNDER_REVIEW:
            raise StateMachineError(
                f"Cannot approve from state {uto.status}; expected UNDER_REVIEW"
            )
        uto.status = TaskStatus.APPROVED
        UTOStateMachine.log_event(uto, "approve_task", actor, "Task approved")

    @staticmethod
    def reject_task(uto: UTO, actor: str = "system", reason: str = "") -> None:
        """Transition under_review → ready, recording why (P1-S3-03)."""
        if uto.status not in (TaskStatus.UNDER_REVIEW, TaskStatus.IN_PROGRESS):
            raise StateMachineError(
                f"Cannot reject from state {uto.status}; expected UNDER_REVIEW"
            )
        uto.status = TaskStatus.READY
        uto.started_at = None
        UTOStateMachine.log_event(
            uto, "reject_task", actor,
            f"Task rejected and returned to ready: {reason}" if reason
            else "Task rejected and returned to ready",
            details={"reason": reason},
        )

    @staticmethod
    def rework_task(uto: UTO, actor: str = "system", reason: str = "") -> None:
        """Transition approved → in_progress for rework (P1-S3-03)."""
        if uto.status not in (TaskStatus.APPROVED, TaskStatus.UNDER_REVIEW):
            raise StateMachineError(
                f"Cannot rework from state {uto.status}; expected APPROVED"
            )
        uto.status = TaskStatus.IN_PROGRESS
        UTOStateMachine.log_event(
            uto, "rework_task", actor,
            f"Task sent for rework: {reason}" if reason else "Task sent for rework",
            details={"reason": reason},
        )

    @staticmethod
    def complete_task(uto: UTO, actor: str = "system") -> None:
        """Transition approved → completed."""
        if uto.status != TaskStatus.APPROVED:
            raise StateMachineError(
                f"Cannot complete from state {uto.status}; expected APPROVED"
            )
        uto.status = TaskStatus.COMPLETED
        UTOStateMachine.log_event(uto, "complete_task", actor, "Task completed")

    @staticmethod
    def block_task(uto: UTO, actor: str = "system", conditions: Optional[list[str]] = None) -> None:
        """Park a task in ``blocked`` and record its unblock conditions (P1-S3-04)."""
        if uto.status == TaskStatus.COMPLETED:
            raise StateMachineError("Cannot block a completed task")
        uto.status = TaskStatus.BLOCKED
        UTOStateMachine.log_event(
            uto, "blocked", actor, "Task blocked",
            details={"unblock_conditions": list(conditions or [])},
        )

    @staticmethod
    def unblock_task(uto: UTO, actor: str = "system") -> None:
        """Return a blocked task to ``ready``."""
        if uto.status != TaskStatus.BLOCKED:
            raise StateMachineError(
                f"Cannot unblock from state {uto.status}; expected BLOCKED"
            )
        uto.status = TaskStatus.READY
        UTOStateMachine.log_event(uto, "unblocked", actor, "Task unblocked")

    @staticmethod
    def revert_state(uto: UTO, target_state: str, actor: str, reason: str = "") -> None:
        """Revert to a previous state (for correction/rework)."""
        if target_state not in ALL_TASK_STATES:
            raise StateMachineError(f"Invalid target state: {target_state}")
        uto.status = target_state
        UTOStateMachine.log_event(
            uto, "revert_state", actor, f"Reverted to {target_state}: {reason}",
            details={"reason": reason},
        )

    @staticmethod
    def log_event(
        uto: UTO,
        event_type: str,
        actor: str = "system",
        description: str = "",
        details: Optional[dict[str, Any]] = None,
    ) -> ExecutionLogEntry:
        """Append an entry to the UTO execution log (the §14 audit trail)."""
        entry = ExecutionLogEntry(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            actor=actor,
            description=description,
            details=details or {},
        )
        uto.execution_log.append(entry)
        return entry
