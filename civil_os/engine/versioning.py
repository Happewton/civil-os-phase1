"""TSD-001 §5.3 r.4 — ECP versioning (content-hash idempotency)."""
from __future__ import annotations


import hashlib
import json
from typing import TYPE_CHECKING


from ..schemas import ECP


if TYPE_CHECKING:
    pass




class ECPVersionManager:
    """§5.3 r.4 — track ECP versions by content hash."""


    # In-memory registry: (project_id, task_id) -> { "version": int, "hash": str }
    _versions: dict = {}


    @staticmethod
    def compute_hash(ecp: ECP) -> str:
        """
        Compute a canonical content hash of the ECP.
        Uses JSON-canonical form (sorted keys, compact output).
        """
        # Serialize ECP to JSON in canonical form
        ecp_dict = ecp.model_dump(exclude={"ecp_id", "created_at", "version", "content_hash"}, by_alias=True)
        canonical_json = json.dumps(ecp_dict, sort_keys=True, separators=(",", ":"), default=str)
        hash_obj = hashlib.sha256(canonical_json.encode("utf-8"))
        return hash_obj.hexdigest()


    @staticmethod
    def register_version(ecp: ECP, project_id: str, task_id: str) -> int:
        """
        Register an ECP and return its version number.
        Idempotent: same content → same version, different content → new version.
        """
        content_hash = ECPVersionManager.compute_hash(ecp)
        key = (project_id, task_id)


        if key not in ECPVersionManager._versions:
            ECPVersionManager._versions[key] = {"version": 1, "hash": content_hash}
            ecp.version = 1
            ecp.content_hash = content_hash
            return 1


        existing = ECPVersionManager._versions[key]
        if existing["hash"] == content_hash:
            # Same content, same version
            ecp.version = existing["version"]
            ecp.content_hash = content_hash
            return existing["version"]


        # Different content, bump version
        new_version = existing["version"] + 1
        ECPVersionManager._versions[key] = {"version": new_version, "hash": content_hash}
        ecp.version = new_version
        ecp.content_hash = content_hash
        return new_version


    @staticmethod
    def get_version(project_id: str, task_id: str) -> int:
        """Retrieve the current version for a (project, task) pair."""
        key = (project_id, task_id)
        if key in ECPVersionManager._versions:
            return ECPVersionManager._versions[key]["version"]
        return 0
