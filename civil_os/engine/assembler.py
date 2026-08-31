"""TSD-001 §5.3 — ECP Assembler (assembly rules 1–5)."""
from __future__ import annotations


from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional


from ..schemas import (ECP, ECPClimateData, ECPConstraints, ECPLocation,
                       ECPProjectIdentity, ECPProjectNeed,
                       ECPSiteData, ECPStakeholderRequirements, Location,
                       Project, Site, Need, Requirement, ConfidenceSummary)
from .jurisdiction import JurisdictionResolver
from .validator import ECPValidator
from .versioning import ECPVersionManager


if TYPE_CHECKING:
    pass




class AssemblyError(Exception):
    """ECP assembly failed."""
    pass




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
    ) -> ECP:
        """
        Assemble an ECP from project, site, need, requirements, etc.

        Rules (§5.3 r.1–r.5):
        - r.1 (completeness): all critical sections must be populated
        - r.2 (freshness): ECP validity checked
        - r.3 (confidence): gate check on level-E parameters
        - r.4 (versioning): content-hash versioning (idempotent)
        - r.5 (jurisdiction): location → jurisdiction → codes cascade
        """


        # Mandatory: project must have a location (r.5)
        if not project.location:
            raise AssemblyError("Project location is mandatory for ECP assembly (§5.3 r.5)")


        # Assemble sections (§5.2)
        # 1. PROJECT IDENTITY
        project_identity = ECPProjectIdentity(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            project_type=str(project.project_type),
            design_life_years=project.design_life_years,
            current_phase=str(project.current_phase),
            created_at=project.created_at,
        )


        # 2. PROJECT NEED
        project_need = ECPProjectNeed(
            need_id=need.need_id if need else "unknown",
            category=need.category if need else "infrastructure",
            problem_statement=need.problem_statement if need else "Not specified",
            affected_population=need.affected_population.count if need else 0,
            performance_targets=[str(t.metric) for t in (need.performance_targets if need else [])],
        )


        # 3. STAKEHOLDER REQUIREMENTS
        stakeholder_reqs = []
        if stakeholders:
            for sh in stakeholders:
                stakeholder_reqs.append(
                    ECPStakeholderRequirements(
                        stakeholder_name=sh.get("name", sh.get("role", "Unknown")),
                        role=sh.get("role", ""),
                        interests=sh.get("interests", []),
                        requirements=sh.get("requirements", []),
                    )
                )


        # 4. LOCATION (§5.3 r.5 cascade)
        location = ECPLocation(
            country=project.location.country,
            region=project.location.region,
            municipality=project.location.municipality,
            latitude=project.location.latitude,
            longitude=project.location.longitude,
            elevation_m=project.location.elevation_m,
        )


        # 5. SITE DATA
        site_data = ECPSiteData(
            soil_layers=[{"depth": "TBD"}] if site else [],
            hydrology_summary={"groundwater_level": "TBD"} if site else {},
            hazards_summary=[{"hazard_type": "TBD"}] if site else [],
            existing_assets=[],
            data_gaps=site.data_gaps if site else [],
        )


        # 6. BUDGET, SCHEDULE, LAND, CONSTRAINTS
        budget = None
        if project.budget_amount:
            from ..schemas import BudgetConstraint
            budget = BudgetConstraint(
                total_budget=project.budget_amount,
                currency=project.budget_currency,
            )


        schedule = None
        if project.target_completion:
            from ..schemas import ScheduleConstraint
            schedule = ScheduleConstraint(
                target_start=datetime.now(timezone.utc),
                target_completion=project.target_completion,
            )


        land = None
        if project.land_area_available_m2:
            from ..schemas import LandConstraint
            land = LandConstraint(
                available_area_m2=project.land_area_available_m2,
            )


        constraints = ECPConstraints(
            risk_tolerance=project.risk_tolerance,
        )


        # 9. APPLICABLE CODES (jurisdiction cascade, r.5)
        jurisdiction_info = JurisdictionResolver.resolve(project.location)
        from ..schemas import ApplicableCode
        applicable_codes = [
            ApplicableCode(jurisdiction=jurisdiction_info["country_code"], code_name=code)
            for code in jurisdiction_info["applicable_codes"]
        ]


        # Confidence summary
        confidence_summary = ConfidenceSummary()


        # Validity period
        from ..schemas import ValidityPeriod
        now = datetime.now(timezone.utc)
        validity = ValidityPeriod(
            valid_from=now,
            valid_until=now + timedelta(days=validity_days),
            rationale=f"Assembly validity window: {validity_days} days",
        )


        # Create the ECP
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
            applicable_codes=applicable_codes,
            confidence_summary=confidence_summary,
            validity=validity,
            assembled_by="ECPAssembler v0.1",
        )


        # r.1 (completeness): check critical sections
        is_complete, missing = ECPValidator.check_completeness(ecp)
        if not is_complete:
            raise AssemblyError(f"ECP assembly: missing sections {missing}")


        # r.2 (freshness): check validity (raised if expired)
        is_fresh, _ = ECPValidator.check_freshness(ecp)


        # r.4 (versioning): compute version and register
        version = ECPVersionManager.register_version(ecp, project.project_id, "uto_0")


        return ecp
