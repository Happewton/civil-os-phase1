"""TSD-001 §5.3 — ECP Assembler (assembly rules 1–5)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ..schemas import (
    ECP,
    ECPClimateData,
    ECPConstraints,
    ECPLocation,
    ECPProjectIdentity,
    ECPProjectNeed,
    ECPSiteData,
    ECPStakeholderRequirements,
    Need,
    Project,
    Requirement,
    Site,
)
from .evidence import EvidenceCounter
from .jurisdiction import JurisdictionResolver
from .validator import ECPValidator
from .versioning import ECPVersionManager


class AssemblyError(Exception):
    """ECP assembly failed."""


class ECPAssembler:
    """§5.3 — assemble ECP from project entities."""

    @staticmethod
    def assemble(
        project: Project,
        site: Optional[Site] = None,
        need: Optional[Need] = None,
        requirements: Optional[list[Requirement]] = None,
        stakeholders: Optional[list] = None,
        validity_days: int = 30,
        version_manager: Optional[ECPVersionManager] = None,
    ) -> ECP:
        """Assemble an ECP from project, site, need, requirements, etc.

        Rules (§5.3 r.1–r.5):
        - r.1 (completeness): all critical sections must be populated
        - r.2 (freshness): ECP validity checked
        - r.3 (confidence): confidence summary populated from evidence
        - r.4 (versioning): content-hash versioning (idempotent)
        - r.5 (jurisdiction): location → jurisdiction → codes cascade
        """
        # Mandatory: project must have a location (r.5)
        if not project.location:
            raise AssemblyError("Project location is mandatory for ECP assembly (§5.3 r.5)")

        # -- 1. PROJECT IDENTITY ---------------------------------------- #
        project_identity = ECPProjectIdentity(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            project_type=project.project_type,
            design_life_years=project.design_life_years,
            current_phase=project.current_phase,
            created_at=project.created_at,
        )

        # -- 2. PROJECT NEED -------------------------------------------- #
        project_need = ECPProjectNeed(
            need_id=need.need_id if need else "unknown",
            category=need.category if need else "infrastructure",
            problem_statement=need.problem_statement if need else "Not specified",
            affected_population=need.affected_population.count if need else 0,
            performance_targets=[t.metric for t in (need.performance_targets if need else [])],
        )

        # -- 3. STAKEHOLDER REQUIREMENTS -------------------------------- #
        stakeholder_reqs = []
        for sh in (stakeholders or []):
            stakeholder_reqs.append(
                ECPStakeholderRequirements(
                    stakeholder_name=sh.get("name", sh.get("role", "Unknown")),
                    role=sh.get("role", ""),
                    interests=sh.get("interests", []),
                    requirements=sh.get("requirements", []),
                    approval_required=bool(sh.get("approval_required", False)),
                )
            )

        # -- 4. LOCATION (§5.3 r.5 cascade) ----------------------------- #
        location = ECPLocation(
            country=project.location.country,
            region=project.location.region,
            municipality=project.location.municipality,
            latitude=project.location.latitude,
            longitude=project.location.longitude,
            elevation_m=project.location.elevation_m,
        )

        # -- 5. SITE DATA ------------------------------------------------ #
        site_data = ECPAssembler._build_site_data(site)

        # -- 6. BUDGET / SCHEDULE / LAND / CONSTRAINTS ------------------ #
        from ..schemas import (
            ApplicableCode,
            BudgetConstraint,
            DesignLife,
            LandConstraint,
            ScheduleConstraint,
            ValidityPeriod,
        )

        budget = None
        if project.budget_amount is not None:
            budget = BudgetConstraint(
                total_budget=project.budget_amount,
                currency=project.budget_currency,
            )

        now = datetime.now(timezone.utc)
        schedule = None
        if project.target_completion:
            schedule = ScheduleConstraint(
                target_start=project.created_at,
                target_completion=project.target_completion,
            )

        land = None
        if project.land_area_available_m2 is not None:
            land = LandConstraint(available_area_m2=project.land_area_available_m2)

        design_life = DesignLife(design_life_years=project.design_life_years)

        # Need constraints are structured (§4.2.2); the ECP section is flat text.
        need_constraints = [
            f"{c.type} ({c.severity}): {c.description}"
            for c in (need.constraints if need else [])
        ]
        constraints = ECPConstraints(
            constraints=need_constraints,
            risk_tolerance=project.risk_tolerance,
        )

        # -- 7. CLIMATE (from the site) --------------------------------- #
        climate = None
        if site is not None:
            climate = ECPClimateData(
                temperature_range=site.climate.temperature_range,
                rainfall_statistics=site.climate.rainfall_statistics,
                seismic_zone=site.geology.seismic_zone,
            )

        # -- 8. APPLICABLE CODES (jurisdiction cascade, r.5) ------------ #
        jurisdiction_info = JurisdictionResolver.resolve(project.location)
        applicable_codes = [
            ApplicableCode(
                jurisdiction=jurisdiction_info["jurisdiction"],
                code_name=code,
                applicability="standard",
            )
            for code in jurisdiction_info["applicable_codes"]
        ]

        validity = ValidityPeriod(
            valid_from=now,
            valid_until=now + timedelta(days=validity_days),
            rationale=f"Assembly validity window: {validity_days} days",
        )

        ecp = ECP(
            project_id=project.project_id,
            project_identity=project_identity,
            project_need=project_need,
            stakeholder_requirements=stakeholder_reqs,
            location=location,
            site_data=site_data,
            budget=budget,
            schedule=schedule,
            land=land,
            constraints=constraints,
            design_life=design_life,
            climate=climate,
            applicable_codes=applicable_codes,
            validity=validity,
            assembled_by="ECPAssembler v0.2",
        )

        # -- 9. CONFIDENCE SUMMARY (r.3) -------------------------------- #
        ecp.confidence_summary = EvidenceCounter.summarise(ecp, site)

        # -- r.1 (completeness) ----------------------------------------- #
        is_complete, missing = ECPValidator.check_completeness(ecp)
        if not is_complete:
            raise AssemblyError(f"ECP assembly: missing sections {missing}")

        # -- r.2 (freshness): raises ValidationError when already expired -- #
        ECPValidator.check_freshness(ecp)

        # -- r.4 (versioning) ------------------------------------------- #
        # A manager is supplied by the CPO so version history is scoped to that
        # project set. Standalone calls fall back to a throwaway manager, which
        # still returns version 1 and a stable content hash.
        manager = version_manager if version_manager is not None else ECPVersionManager()
        manager.register_version(ecp, project.project_id, "uto_0")

        return ecp

    @staticmethod
    def _build_site_data(site: Optional[Site]) -> ECPSiteData:
        """Project SITE (§4.2.4) into the ECP SITE DATA section (§5.2.5)."""
        if site is None:
            return ECPSiteData()

        soil_layers: list[dict[str, Any]] = []
        for profile in site.soil_profiles:
            for layer in profile.layers:
                soil_layers.append({
                    "profile_id": profile.profile_id,
                    "borehole_id": profile.borehole_id,
                    "depth_from_m": layer.depth_from_m,
                    "depth_to_m": layer.depth_to_m,
                    "soil_type": layer.soil_type,
                    "classification": layer.classification,
                    "properties": layer.properties.model_dump(mode="json"),
                    "confidence_level": layer.confidence_level,
                })

        hydrology_summary: dict[str, Any] = {}
        if site.hydrology.groundwater_level is not None:
            hydrology_summary["groundwater_level"] = \
                site.hydrology.groundwater_level.model_dump(mode="json")
        if site.hydrology.design_storm is not None:
            hydrology_summary["design_storm"] = \
                site.hydrology.design_storm.model_dump(mode="json")
        if site.hydrology.return_period_years is not None:
            hydrology_summary["return_period_years"] = site.hydrology.return_period_years
        if site.hydrology.catchment_area_km2 is not None:
            hydrology_summary["catchment_area_km2"] = site.hydrology.catchment_area_km2

        return ECPSiteData(
            soil_layers=soil_layers,
            hydrology_summary=hydrology_summary,
            hazards_summary=[h.model_dump(mode="json") for h in site.hazards],
            existing_assets=[a.model_dump(mode="json") for a in site.existing_assets],
            data_gaps=list(site.data_gaps),
        )
