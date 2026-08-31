"""Pytest configuration and fixtures for CIVIL-OS tests."""
import pytest
from civil_os import CivilProjectOrchestrator
from civil_os.schemas import (Location, Need, Project, ProjectType, Site,
                              Requirement, AffectedPopulation)


@pytest.fixture
def cpo():
    """Provide a fresh CPO instance for each test."""
    return CivilProjectOrchestrator()


@pytest.fixture
def project(cpo):
    """Create a test project (Al-Wadi flood protection scenario)."""
    return cpo.create_project(
        name="Al-Wadi Flood Protection",
        project_type="water",
        country="SA",
        latitude=24.7136,
        longitude=46.6753,
        region="Riyadh",
        municipality="Al-Wadi",
        description="Flood protection for 10,000 people in Al-Wadi",
        budget_amount=15000000,
        design_life_years=50,
    )


@pytest.fixture
def site(cpo, project):
    """Create a test site."""
    site_obj = Site(
        project_id=project.project_id,
        data_gaps=["Groundwater levels", "Soil boring data"],
        recommended_investigations=["Geotechnical survey", "Hydrological study"],
    )
    cpo.register_site(project.project_id, site_obj)
    return site_obj


@pytest.fixture
def need(cpo, project):
    """Create a test need."""
    need_obj = Need(
        project_id=project.project_id,
        category="safety",
        problem_statement="Protect 10,000 residents from seasonal flooding",
        affected_population=AffectedPopulation(
            count=10000,
            description="Al-Wadi settlement",
            vulnerable_groups=["children", "elderly"],
        ),
    )
    cpo.register_need(project.project_id, need_obj)
    return need_obj


@pytest.fixture
def requirement(cpo, project):
    """Create a test requirement."""
    req_obj = Requirement(
        project_id=project.project_id,
        discipline="civil",
        category="safety",
        description="Design flood barrier for 100-year storm",
    )
    cpo.register_requirement(project.project_id, req_obj)
    return req_obj
