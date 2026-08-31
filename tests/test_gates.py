"""Tests for confidence gates and waivers."""
import pytest
from civil_os.schemas import UTO, ConfidenceLevel, AssumptionItem, Waiver
from civil_os.engine import ConfidenceGate, TaskStatus, ECPRef


def test_gate_blocks_safety_critical_level_e(cpo, project):
    """Test that gate blocks safety-critical tasks with level-E assumptions."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(
        project_id=project.project_id,
        ecp_id=ecp.ecp_id,
        task_name="Safety-critical design",
        discipline="civil",
        safety_critical=True,
        assumptions=[
            AssumptionItem(
                assumption_text="Groundwater level is 5m deep",
                confidence_level=ConfidenceLevel.E,
            )
        ],
    )
    
    can_proceed, issues = cpo.check_gate(task.uto_id)
    assert can_proceed is False
    assert len(issues) > 0


def test_gate_blocks_non_safety_critical_without_waiver(cpo, project):
    """Test that gate blocks non-safety-critical tasks with level-E unless waived."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(
        project_id=project.project_id,
        ecp_id=ecp.ecp_id,
        task_name="Non-critical analysis",
        discipline="civil",
        safety_critical=False,
        assumptions=[
            AssumptionItem(
                assumption_text="Soil friction angle 35 degrees",
                confidence_level=ConfidenceLevel.E,
            )
        ],
    )
    
    can_proceed, issues = cpo.check_gate(task.uto_id)
    assert can_proceed is False
    assert len(issues) > 0


def test_gate_passes_with_waiver(cpo, project):
    """Test that gate passes non-safety-critical task when waived."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(
        project_id=project.project_id,
        ecp_id=ecp.ecp_id,
        task_name="Non-critical analysis",
        discipline="civil",
        safety_critical=False,
        assumptions=[
            AssumptionItem(
                assumption_text="Soil friction angle 35 degrees",
                confidence_level=ConfidenceLevel.E,
            )
        ],
    )
    
    # Apply waiver
    waiver = Waiver(
        parameter="Soil friction angle 35 degrees",
        rationale="Engineering judgment based on regional standards",
        waived_by="Chief Engineer",
    )
    cpo.apply_waiver(task.uto_id, waiver)
    
    can_proceed, issues = cpo.check_gate(task.uto_id)
    assert can_proceed is True
    assert len(issues) == 0


def test_gate_never_accepts_waiver_for_safety_critical(cpo, project):
    """Test that gate never accepts waiver for safety-critical parameters."""
    ecp = cpo.assemble_ecp(project.project_id)
    task = cpo.create_task(
        project_id=project.project_id,
        ecp_id=ecp.ecp_id,
        task_name="Safety-critical design",
        discipline="civil",
        safety_critical=True,
        assumptions=[
            AssumptionItem(
                assumption_text="Peak ground acceleration is 0.25g",
                confidence_level=ConfidenceLevel.E,
            )
        ],
    )
    
    # Try to apply waiver (should fail or be ignored)
    from civil_os.engine import AssemblyError
    waiver = Waiver(
        parameter="Peak ground acceleration is 0.25g",
        rationale="Engineering estimate",
        waived_by="Designer",
    )
    
    with pytest.raises(AssemblyError):
        cpo.apply_waiver(task.uto_id, waiver)
