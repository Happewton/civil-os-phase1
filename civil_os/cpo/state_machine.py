"""TSD-001 §6.3 — UTO lifecycle state machine."""
from __future__ import annotations


from enum import Enum
from typing import TYPE_CHECKING


from ..schemas import TaskStatus, UTO, ExecutionLogEntry


if TYPE_CHECKING:
    pass




class StateMachineError(Exception):
    """State transition invalid."""
    pass




class UTOStateMachine:
    """§6.3 — UTO lifecycle state machine.

    States: ready → in_progress → under_review → approved → completed

    Transitions:
    - ready → in_progress (start_task)
    - in_progress → under_review (mark_under_review, if requires_review else → approved)
    - under_review → approved (approve_task)
    - approved → completed (complete_task)
    - any state → any state (for reverting/correction, with reason)
    """


    @staticmethod
    def start_task(uto: UTO, actor: str = "system") -> None:
        """Transition ready → in_progress."""
        if uto.status != TaskStatus.READY:
            raise StateMachineError(
                f"Cannot start task in state {uto.status}; expected READY"
            )


        uto.status = TaskStatus.IN_PROGRESS
        UTOStateMachine._log_transition(uto, "start_task", actor, "Task started")


    @staticmethod
    def mark_under_review(uto: UTO, actor: str = "system") -> None:
        """Transition in_progress → under_review (or → approved if no review required)."""
        if uto.status != TaskStatus.IN_PROGRESS:
            raise StateMachineError(
                f"Cannot mark under review from state {uto.status}; expected IN_PROGRESS"
            )


        if uto.requires_review:
            uto.status = TaskStatus.UNDER_REVIEW
            UTOStateMachine._log_transition(uto, "mark_under_review", actor, "Task marked for review")
        else:
            # Auto-approve if no review required
            uto.status = TaskStatus.APPROVED
            UTOStateMachine._log_transition(uto, "auto_approve", actor, "Task approved (no review required)")


    @staticmethod
    def approve_task(uto: UTO, actor: str = "system") -> None:
        """Transition under_review → approved."""
        if uto.status != TaskStatus.UNDER_REVIEW:
            raise StateMachineError(
                f"Cannot approve from state {uto.status}; expected UNDER_REVIEW"
            )


        uto.status = TaskStatus.APPROVED
        UTOStateMachine._log_transition(uto, "approve_task", actor, "Task approved")


    @staticmethod
    def complete_task(uto: UTO, actor: str = "system") -> None:
        """Transition approved → completed."""
        if uto.status != TaskStatus.APPROVED:
            raise StateMachineError(
                f"Cannot complete from state {uto.status}; expected APPROVED"
            )


        uto.status = TaskStatus.COMPLETED
        UTOStateMachine._log_transition(uto, "complete_task", actor, "Task completed")


    @staticmethod
    def revert_state(uto: UTO, target_state: str, actor: str, reason: str = "") -> None:
        """Revert to a previous state (for correction/rework)."""
        valid_states = [TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.UNDER_REVIEW,
                        TaskStatus.APPROVED, TaskStatus.COMPLETED]
        if target_state not in valid_states:
            raise StateMachineError(f"Invalid target state: {target_state}")


        uto.status = target_state
        UTOStateMachine._log_transition(uto, "revert_state", actor, f"Reverted to {target_state}: {reason}")


    @staticmethod
    def _log_transition(uto: UTO, event_type: str, actor: str, description: str) -> None:
        """Log a state transition to the execution log."""
        from datetime import datetime, timezone
        entry = ExecutionLogEntry(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            actor=actor,
            description=description,
        )
        uto.execution_log.append(entry)
