"""Tests for jurisdiction cascade."""
import pytest
from civil_os.engine import JurisdictionResolver
from civil_os.schemas import Location


def test_jurisdiction_resolution_saudi_arabia():
    """Test jurisdiction resolution for Saudi Arabia."""
    location = Location(
        country="SA",
        region="Riyadh",
        municipality="Al-Wadi",
        latitude=24.7136,
        longitude=46.6753,
    )
    
    result = JurisdictionResolver.resolve(location)
    assert result["country_code"] == "SA"
    assert "SBC" in result["applicable_codes"][0]
    assert "Al-Wadi" in result["jurisdiction"]


def test_jurisdiction_resolution_united_states():
    """Test jurisdiction resolution for United States."""
    location = Location(
        country="US",
        region="California",
        municipality="San Francisco",
        latitude=37.7749,
        longitude=-122.4194,
    )
    
    result = JurisdictionResolver.resolve(location)
    assert result["country_code"] == "US"
    assert any("IBC" in code or "ACI" in code or "AASHTO" in code
               for code in result["applicable_codes"])


def test_jurisdiction_resolution_fallback():
    """Test jurisdiction resolution fallback to International."""
    location = Location(
        country="ZZ",  # Invalid country code
        latitude=0,
        longitude=0,
    )
    
    result = JurisdictionResolver.resolve(location)
    assert result["country_code"] == "INT"
    assert "ISO" in result["applicable_codes"][0] or "Eurocode" in result["applicable_codes"][0]


def test_code_details_lookup():
    """Test code details lookup."""
    details = JurisdictionResolver.get_code_details("SA", "SBC 401")
    assert details is not None
    assert "SBC" in details["code_name"]
    assert details["country"] == "Saudi Arabia"
