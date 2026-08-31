"""Tests for ECP assembly and validation."""
import pytest
from datetime import datetime, timezone, timedelta
from civil_os.engine import ECPAssembler, ECPValidator, AssemblyError, ValidationError


def test_ecp_assembly_requires_location(cpo, project):
    """Test that ECP assembly requires a project location."""
    # Remove location to trigger error
    project.location = None
    
    with pytest.raises(AssemblyError):
        cpo.assemble_ecp(project.project_id)


def test_ecp_assembly_success(cpo, project, site, need):
    """Test successful ECP assembly."""
    ecp = cpo.assemble_ecp(project.project_id, site_id=site.site_id, need_id=need.need_id)
    
    assert ecp.ecp_id is not None
    assert ecp.project_id == project.project_id
    assert ecp.version == 1
    assert ecp.content_hash != ""
    assert ecp.project_identity.project_id == project.project_id
    assert ecp.location.country == "SA"


def test_ecp_completeness_check(cpo, project):
    """Test ECP completeness validation."""
    ecp = cpo.assemble_ecp(project.project_id)
    
    is_complete, missing = ECPValidator.check_completeness(ecp)
    assert is_complete is True
    assert len(missing) == 0


def test_ecp_freshness_check(cpo, project):
    """Test ECP freshness validation."""
    ecp = cpo.assemble_ecp(project.project_id, validity_days=30)
    
    is_fresh, warnings = ECPValidator.check_freshness(ecp)
    assert is_fresh is True


def test_ecp_freshness_check_expired():
    """Test that expired ECP raises error."""
    from civil_os.schemas import ECP, ECPProjectIdentity, ECPProjectNeed, ValidityPeriod, Location as ECPLoc, ECPSiteData, ConfidenceSummary, ECPLocation
    from datetime import timedelta
    
    expired_validity = ValidityPeriod(
        valid_from=datetime.now(timezone.utc) - timedelta(days=60),
        valid_until=datetime.now(timezone.utc) - timedelta(days=30),
    )
    
    ecp = ECP(
        project_id="test",
        project_identity=ECPProjectIdentity(
            project_id="test",
            name="Test",
            project_type="water",
            design_life_years=50,
            current_phase="feasibility",
            created_at=datetime.now(timezone.utc),
        ),
        project_need=ECPProjectNeed(
            need_id="need-1",
            category="safety",
            problem_statement="Test",
        ),
        location=ECPLocation(country="SA", latitude=0, longitude=0),
        site_data=ECPSiteData(),
        validity=expired_validity,
        confidence_summary=ConfidenceSummary(),
    )
    
    with pytest.raises(ValidationError):
        ECPValidator.check_freshness(ecp)


def test_ecp_versioning_idempotency(cpo, project):
    """Test that identical ECP content produces same version."""
    from civil_os.engine import ECPVersionManager
    
    ecp1 = cpo.assemble_ecp(project.project_id, validity_days=30)
    v1 = ecp1.version
    h1 = ecp1.content_hash
    
    # Re-assemble: should get same version if content is identical
    ecp2 = cpo.assemble_ecp(project.project_id, validity_days=30)
    v2 = ecp2.version
    h2 = ecp2.content_hash
    
    # Content should hash to same value (idempotent)
    assert h1 == h2
