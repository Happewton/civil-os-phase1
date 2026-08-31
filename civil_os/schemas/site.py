"""TSD-001 §4.2.4 — SITE entity (terrain, geology, soils, hydrology,
climate, hazards, existing assets, constraints)."""
from __future__ import annotations


from typing import Any, Literal, Optional


from pydantic import Field, field_validator, model_validator


from .base import CivilOSModel, ConfidenceLevel, ParameterEvidence, derive_risk_level, new_id




# --------------------------------------------------------------------------- #
# Geometry (RFC 7946)
# --------------------------------------------------------------------------- #


class GeoJSONGeometry(CivilOSModel):
    type: Literal["Point", "MultiPoint", "LineString", "Polygon", "MultiPolygon"]
    coordinates: Any


    @field_validator("coordinates")
    @classmethod
    def _coordinates_required(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("GeoJSON geometry requires coordinates")
        return value




class Boundary(CivilOSModel):
    type: Literal["polygon", "multipolygon"]
    coordinates: Any
    area_m2: float = Field(..., ge=0)




# --------------------------------------------------------------------------- #
# Soils
# --------------------------------------------------------------------------- #


class SoilLayerProperties(CivilOSModel):
    unit_weight_kn_m3: Optional[float] = Field(None, ge=0)
    cohesion_kpa: Optional[float] = Field(None, ge=0)
    friction_angle_deg: Optional[float] = Field(None, ge=0, le=60)
    permeability_m_s: Optional[float] = None
    compressibility: Optional[float] = None




class SoilLayer(CivilOSModel):
    depth_from_m: float = Field(..., ge=0)
    depth_to_m: float = Field(..., gt=0)
    soil_type: str
    classification: str = ""
    properties: SoilLayerProperties = Field(default_factory=SoilLayerProperties)
    confidence_level: ConfidenceLevel = ConfidenceLevel.E


    @model_validator(mode="after")
    def _depths_ordered(self) -> "SoilLayer":
        if self.depth_to_m <= self.depth_from_m:
            raise ValueError("depth_to_m must be greater than depth_from_m")
        return self




class SoilProfile(CivilOSModel):
    profile_id: str = Field(default_factory=new_id)
    location: Optional[GeoJSONGeometry] = None
    borehole_id: str = ""
    layers: list[SoilLayer] = Field(default_factory=list)




# --------------------------------------------------------------------------- #
# Terrain / geology / hydrology / climate
# --------------------------------------------------------------------------- #


class Terrain(CivilOSModel):
    elevation_model_id: Optional[str] = None
    slope_map_id: Optional[str] = None
    drainage_paths: list[GeoJSONGeometry] = Field(default_factory=list)
    water_bodies: list[GeoJSONGeometry] = Field(default_factory=list)




class Geology(CivilOSModel):
    geological_map_id: Optional[str] = None
    rock_types: list[str] = Field(default_factory=list)
    fault_lines: list[GeoJSONGeometry] = Field(default_factory=list)
    seismic_zone: str = ""




class Hydrology(CivilOSModel):
    """Carries full §7.2 evidence records for groundwater and design storm."""
    catchment_area_km2: Optional[float] = Field(None, gt=0)
    design_storm: Optional[ParameterEvidence] = None
    return_period_years: Optional[int] = Field(None, ge=1)
    rainfall_data_source: str = ""
    flood_zones: list[GeoJSONGeometry] = Field(default_factory=list)
    groundwater_level: Optional[ParameterEvidence] = None
    aquifer_characteristics: Optional[dict] = None




class WindData(CivilOSModel):
    basic_wind_speed: ParameterEvidence
    wind_direction_distribution: Optional[dict] = None
    terrain_category: str = ""
    return_period_years: int = Field(50, ge=1)




class SeismicData(CivilOSModel):
    peak_ground_acceleration: ParameterEvidence
    seismic_zone: str = ""
    soil_class: str = ""
    return_period_years: int = Field(475, ge=1)




class ClimateData(CivilOSModel):
    temperature_range: Optional[dict] = None
    rainfall_statistics: Optional[dict] = None
    humidity_range: Optional[dict] = None
    solar_radiation: Optional[dict] = None
    snow_load: Optional[dict] = None
    wind: Optional[WindData] = None
    seismic: Optional[SeismicData] = None




# --------------------------------------------------------------------------- #
# Hazards / assets / constraints / SITE
# --------------------------------------------------------------------------- #


class Hazard(CivilOSModel):
    hazard_type: str = Field(
        ..., description="flood | earthquake | landslide | wind | fire | erosion | ...")
    description: str = ""
    probability: Literal["negligible", "low", "medium", "high", "certain"] = "low"
    consequence: Literal["insignificant", "minor", "moderate", "major",
                         "catastrophic"] = "minor"
    risk_level: Optional[Literal["low", "medium", "high", "extreme"]] = None
    mitigation_required: bool = False


    @model_validator(mode="before")
    @classmethod
    def _derive_risk_level(cls, data):
        if isinstance(data, dict) and data.get("risk_level") is None:
            data = dict(data)
            data["risk_level"] = derive_risk_level(
                data.get("probability", "low"), data.get("consequence", "minor"))
        return data




class ExistingAsset(CivilOSModel):
    asset_type: str
    description: str = ""
    location: Optional[GeoJSONGeometry] = None
    condition: Literal["excellent", "good", "fair", "poor", "critical"] = "fair"
    owner: str = ""




class SiteConstraint(CivilOSModel):
    type: Literal["protected_area", "archaeological", "utility", "access",
                  "noise", "other"] = "other"
    description: str
    buffer_m: float = Field(0.0, ge=0)
    regulatory_reference: str = ""




class Site(CivilOSModel):
    """TSD-001 §4.2.4 — SITE."""


    site_id: str = Field(default_factory=new_id)
    project_id: str
    boundary: Optional[Boundary] = None
    terrain: Terrain = Field(default_factory=Terrain)
    geology: Geology = Field(default_factory=Geology)
    soil_profiles: list[SoilProfile] = Field(default_factory=list)
    hydrology: Hydrology = Field(default_factory=Hydrology)
    climate: ClimateData = Field(default_factory=ClimateData)
    hazards: list[Hazard] = Field(default_factory=list)
    existing_assets: list[ExistingAsset] = Field(default_factory=list)
    constraints: list[SiteConstraint] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    recommended_investigations: list[str] = Field(default_factory=list)
