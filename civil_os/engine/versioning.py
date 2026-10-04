"""TSD-001 §5.3 r.4 — ECP versioning (content-hash idempotency).

The content hash covers the *engineering content* of a packet only. Fields that
change on every assembly (assembly timestamp, identity, the validity window)
are excluded, so re-assembling unchanged inputs yields the same hash and
therefore the same version number (ROADMAP-001 P1-S1-02 / test TC-003).
"""
from __future__ import annotations

import hashlib
import json
from threading import RLock
from typing import Any

from ..schemas import ECP

#: Metadata that must not influence the content hash. ``validity`` is excluded
#: because ``valid_from``/``valid_until`` are derived from wall-clock time at
#: assembly, which would make every re-assembly look like a content change.
NON_CONTENT_FIELDS = frozenset({"ecp_id", "created_at", "version", "content_hash", "validity"})


class ECPVersionManager:
    """§5.3 r.4 — track ECP versions by content hash.

    State is per-instance so that independent registries, projects and test
    runs never share version history. The CPO owns one manager and passes it to
    :meth:`ECPAssembler.assemble`.
    """

    def __init__(self) -> None:
        self._versions: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = RLock()

    def compute_hash(self, ecp: ECP) -> str:
        """Canonical SHA-256 of the ECP's engineering content.

        Serialises in JSON mode with sorted keys and compact separators so the
        hash is stable across processes and Python versions.
        """
        payload = ecp.model_dump(mode="json", exclude=set(NON_CONTENT_FIELDS))
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def register_version(self, ecp: ECP, project_id: str, task_id: str) -> int:
        """Assign a version to ``ecp`` and stamp it in place.

        Idempotent: identical content keeps the current version, changed content
        increments it.
        """
        content_hash = self.compute_hash(ecp)
        key = (project_id, task_id)

        with self._lock:
            existing = self._versions.get(key)
            if existing is None:
                version = 1
            elif existing["hash"] == content_hash:
                version = existing["version"]
            else:
                version = existing["version"] + 1

            self._versions[key] = {"version": version, "hash": content_hash}
            ecp.version = version
            ecp.content_hash = content_hash
            return version

    def get_version(self, project_id: str, task_id: str) -> int:
        """Current version for a (project, task) pair; 0 when never registered."""
        with self._lock:
            entry = self._versions.get((project_id, task_id))
            return entry["version"] if entry else 0

    def get_hash(self, project_id: str, task_id: str) -> str:
        """Content hash for a (project, task) pair; empty when never registered."""
        with self._lock:
            entry = self._versions.get((project_id, task_id))
            return entry["hash"] if entry else ""
