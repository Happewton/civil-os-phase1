"""Tests for CPO (Civil Project Orchestrator)."""
import pytest
import json
from civil_os.cpo import CivilProjectOrchestrator
from civil_os.schemas import Need, Site


def test_cpo_project_creation(cpo):
    """Test CPO project creation."""
    project = cpo.create_project(
        name="Test Project",
        project_type="water",
        country="US",
        latitude=40.7128,
        longitude=-74.0060,
    )
    
    assert project.project_id is not None
    assert project.name == "Test Project"
    
    retrieved = cpo.get_project(project.project_id)
    assert retrieved is not None
    assert retrieved.project_id == project.project_id


def test_cpo_site_registration(cpo, project):
    """Test CPO site registration."""
    site = Site(project_id=project.project_id)
    site_id = cpo.register_site(project.project_id, site)
    
    retrieved_site = cpo.registry.get_site(site_id)
    assert retrieved_site is not None
    assert retrieved_site.project_id == project.project_id


def test_cpo_need_registration(cpo, project):
    """Test CPO need registration."""
    need = Need(
        project_id=project.project_id,
        category="infrastructure",
        problem_statement="Test need",
    )
    need_id = cpo.register_need(project.project_id, need)
    
    retrieved_need = cpo.registry.get_need(need_id)
    assert retrieved_need is not None
    assert retrieved_need.category == "infrastructure"


def test_cpo_json_persistence(cpo, project):
    """Test CPO JSON export/import."""
    # Add some data
    ecp = cpo.assemble_ecp(project.project_id)
    
    # Export
    json_str = cpo.export_json()
    assert json_str is not None
    data = json.loads(json_str)
    assert "projects" in data
    assert "ecps" in data
    
    # Import into new CPO
    cpo2 = CivilProjectOrchestrator()
    cpo2.import_json(json_str)
    
    # Verify data was imported
    project2 = cpo2.get_project(project.project_id)
    assert project2 is not None
    assert project2.name == project.name
    
    ecps = cpo2.get_ecps_for_project(project.project_id)
    assert len(ecps) > 0


def test_cpo_lists_projects(cpo, project):
    """Test CPO lists all projects."""
    projects = cpo.registry.list_projects()
    assert len(projects) >= 1
    assert any(p.project_id == project.project_id for p in projects)
