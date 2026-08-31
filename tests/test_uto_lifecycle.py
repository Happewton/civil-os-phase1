"""Tests for UTO lifecycle state machine."""
import pytest
from civil_os.cpo import UTOStateMachine
from civil_os.cpo.state_machine import StateMachineError
from civil_os.schemas import UTO, TaskStatus, ECPRef


def test_uto_lifecycle_ready_to_completed(cpo, project):
    """Test complete UTO lifecycle: ready → in_progress → under_review → approved → completed."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(
        project_id=project.project_id,
        ecp_id=ecp.ecp_id,
        task_name="Design analysis",
        discipline="civil",
        requires_review=True,
    )
    
    assert task.status == TaskStatus.READY
    
    # Start task
    cpo.start_task(task.uto_id, actor="Engineer")
    task = cpo.get_task(task.uto_id)
    assert task.status == TaskStatus.IN_PROGRESS
    
    # Mark under review
    cpo.mark_under_review(task.uto_id, actor="Engineer")
    task = cpo.get_task(task.uto_id)
    assert task.status == TaskStatus.UNDER_REVIEW
    
    # Approve
    cpo.approve_task(task.uto_id, actor="Reviewer")
    task = cpo.get_task(task.uto_id)
    assert task.status == TaskStatus.APPROVED
    
    # Complete
    cpo.complete_task(task.uto_id, actor="Engineer")
    task = cpo.get_task(task.uto_id)
    assert task.status == TaskStatus.COMPLETED


def test_uto_auto_approve_when_no_review_required(cpo, project):
    """Test that non-review tasks auto-approve after in_progress."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(
        project_id=project.project_id,
        ecp_id=ecp.ecp_id,
        task_name="Simple task",
        discipline="civil",
        requires_review=False,  # No review required
    )
    
    cpo.start_task(task.uto_id)
    cpo.mark_under_review(task.uto_id)
    
    task = cpo.get_task(task.uto_id)
    # Should auto-transition to APPROVED (skipping UNDER_REVIEW)
    assert task.status == TaskStatus.APPROVED


def test_invalid_state_transition():
    """Test that invalid state transitions raise errors."""
    task = UTO(
        project_id="proj-1",
        ecp_ref=None,
        task_name="Test task",
        discipline="civil",
        task_type="design",
        status=TaskStatus.READY,
    )
    
    # Try to approve from READY (should fail, need IN_PROGRESS first)
    with pytest.raises(StateMachineError):
        UTOStateMachine.approve_task(task)


def test_execution_log_records_transitions(cpo, project):
    """Test that execution log records all state transitions."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(
        project_id=project.project_id,
        ecp_id=ecp.ecp_id,
        task_name="Logged task",
        discipline="civil",
    )
    
    initial_log_len = len(task.execution_log)
    
    cpo.start_task(task.uto_id, actor="TestActor")
    task = cpo.get_task(task.uto_id)
    
    # Should have new log entry
    assert len(task.execution_log) > initial_log_len
    latest_entry = task.execution_log[-1]
    assert latest_entry.event_type == "start_task"
    assert latest_entry.actor == "TestActor"
