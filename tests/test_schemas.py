"""Tests for CIVIL-OS core schemas."""
import pytest
from civil_os.schemas import (
    Project, ProjectType, ProjectStatus, Location, Site, Need, Requirement,
    ConfidenceLevel, ParameterEvidence, EvidenceStatus, Hazard, UTO, TaskStatus
)


def test_project_creation(project):
    """Test project creation."""
    assert project.name == "Al-Wadi Flood Protection"
    assert project.project_type == "water"
    assert project.status == ProjectStatus.DRAFT
    assert project.location is not None
    assert project.location.country == "SA"


def test_location_validation():
    """Test location validation."""
    loc = Location(
        country="SA",
        latitude=24.7136,
        longitude=46.6753,
    )
    assert loc.country == "SA"
    
    with pytest.raises(ValueError):
        Location(country="SA", latitude=91, longitude=0)  # Invalid latitude


def test_site_creation(site):
    """Test site creation."""
    assert site.site_id is not None
    assert "Groundwater" in site.data_gaps[0]


def test_need_creation(need):
    """Test need creation."""
    assert need.need_id is not None
    assert need.category == "safety"
    assert need.affected_population.count == 10000


def test_requirement_creation(requirement):
    """Test requirement creation."""
    assert requirement.requirement_id is not None
    assert requirement.discipline == "civil"
    assert requirement.category == "safety"


def test_parameter_evidence():
    """Test parameter evidence creation."""
    evidence = ParameterEvidence(
        parameter="groundwater_level",
        value=5.2,
        unit="m",
        confidence_level=ConfidenceLevel.E,
        status=EvidenceStatus.MUST_BE_VERIFIED,
        source="Assumption",
    )
    assert evidence.confidence_level == ConfidenceLevel.E
    assert evidence.status == EvidenceStatus.MUST_BE_VERIFIED


def test_hazard_risk_derivation():
    """Test hazard risk level derivation."""
    hazard = Hazard(
        hazard_type="flood",
        probability="high",
        consequence="major",
    )
    assert hazard.risk_level == "high"


def test_uto_creation():
    """Test UTO (task) creation."""
    task = UTO(
        project_id="proj-123",
        ecp_ref=None,
        task_name="Design flood barrier",
        discipline="civil",
        task_type="design",
        safety_critical=True,
    )
    assert task.uto_id is not None
    assert task.status == TaskStatus.READY
    assert task.safety_critical is True
