"""TSD-001 §5.3 r.1 — Requirements matrix and completeness tracking."""
from __future__ import annotations


from typing import TYPE_CHECKING


from ..schemas import ECP, Project, Requirement, UTO


if TYPE_CHECKING:
    pass




class RequirementsMatrix:
    """Maps requirements across phases and disciplines to tasks."""


    @staticmethod
    def create_matrix(
        project: Project,
        requirements: list[Requirement],
        tasks: list[UTO],
    ) -> dict:
        """
        Create a requirement traceability matrix.
        Returns { req_id: { "requirement": Requirement, "satisfied_by": [task_ids] } }
        """
        matrix = {}


        for req in requirements:
            satisfied_by = []
            for task in tasks:
                for req_ref in task.requirements_satisfied:
                    if req_ref.requirement_id == req.requirement_id:
                        satisfied_by.append(task.uto_id)


            matrix[req.requirement_id] = {
                "requirement": req,
                "satisfied_by": satisfied_by,
            }


        return matrix


    @staticmethod
    def check_coverage(matrix: dict) -> tuple[bool, list[str]]:
        """
        Check if all requirements are satisfied by at least one task.
        Returns (all_covered, list_of_uncovered_req_ids).
        """
        uncovered = []


        for req_id, entry in matrix.items():
            if not entry["satisfied_by"]:
                uncovered.append(req_id)


        return len(uncovered) == 0, uncovered
