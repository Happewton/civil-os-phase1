"""TSD-001 §5.3 r.5 — Jurisdiction → regulations → codes cascade."""
from __future__ import annotations


from typing import TYPE_CHECKING, Optional


from ..schemas import Location


if TYPE_CHECKING:
    pass




# Codes registry (Phase-1: SA, US, GB, DE + fallback)
CODES_REGISTRY = {
    "SA": {
        "country": "Saudi Arabia",
        "codes": ["SBC 401 (Structural Design)", "SBC 402 (Geotechnics)"],
    },
    "US": {
        "country": "United States",
        "codes": ["IBC (International Building Code)", "ACI 318 (Concrete)", "AASHTO (Roads)"],
    },
    "GB": {
        "country": "United Kingdom",
        "codes": ["BS 8103 (Foundations)", "BS 6399 (Loading)", "CHLP (Heritage)"],
    },
    "DE": {
        "country": "Germany",
        "codes": ["DIN 1054 (Geotechnics)", "DIN 1055 (Loading)", "EC2 (Eurocodes)"],
    },
    "INT": {
        "country": "International",
        "codes": ["ISO 2394 (Reliability)", "EN Eurocodes"],
    },
}




class JurisdictionResolver:
    """§5.3 r.5 — resolve location → codes cascade."""


    @staticmethod
    def resolve(location: Location) -> dict:
        """
        Given a location (country, region, municipality), resolve the applicable codes.
        Returns { "country_code": str, "jurisdiction": str, "applicable_codes": [str] }
        """
        country_code = location.country.upper()


        if country_code not in CODES_REGISTRY:
            country_code = "INT"  # fallback to International


        registry_entry = CODES_REGISTRY[country_code]


        return {
            "country_code": country_code,
            "country_name": registry_entry["country"],
            "jurisdiction": f"{location.municipality or location.region or location.country}",
            "applicable_codes": registry_entry["codes"],
            "location": location,
        }


    @staticmethod
    def get_code_details(country_code: str, code_name: str) -> Optional[dict]:
        """
        Retrieve details for a specific code.
        Phase-1: simple registry; production → detailed database.
        """
        country_code = country_code.upper()
        if country_code not in CODES_REGISTRY:
            country_code = "INT"


        codes = CODES_REGISTRY[country_code].get("codes", [])
        for code in codes:
            if code_name.lower() in code.lower():
                return {
                    "code_name": code,
                    "country": CODES_REGISTRY[country_code]["country"],
                    "applicability": "standard",
                }


        return None
