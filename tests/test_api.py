"""Tests for the FastAPI service (TSD-001 §24 API contract, §25 error taxonomy)."""
from __future__ import annotations

import importlib
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("CIVIL_OS_SEED", "0")


@pytest.fixture
def client():
    """A client over a freshly built app, isolated from the module-level CPO."""
    import app.api as api

    module = importlib.reload(api)
    module.SEED_ON_START = False
    with TestClient(module.app) as test_client:
        test_client.module = module
        yield test_client


@pytest.fixture
def project(client):
    res = client.post("/api/v1/projects", json={
        "name": "Al-Wadi Flood Protection",
        "project_type": "water",
        "country": "SA",
        "region": "Riyadh Province",
        "municipality": "Al-Wadi",
        "latitude": 24.7136,
        "longitude": 46.6753,
        "budget_amount": 15_000_000,
        "risk_tolerance": "conservative",
    })
    assert res.status_code == 201, res.text
    return res.json()


def _make_site(client, project_id):
    res = client.post(f"/api/v1/projects/{project_id}/sites", json={
        "name": "Al-Wadi Site",
        "data_gaps": ["Groundwater level"],
    })
    assert res.status_code == 201, res.text
    return res.json()


def _make_ecp(client, project_id, site_id=None, need_id=None):
    params = {}
    if site_id:
        params["site_id"] = site_id
    if need_id:
        params["need_id"] = need_id
    res = client.post(f"/api/v1/projects/{project_id}/ecps", params=params)
    assert res.status_code == 200, res.text
    return res.json()


# --------------------------------------------------------------------------- #
# Health & error envelope
# --------------------------------------------------------------------------- #
def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["version"]


def test_error_envelope_shape(client):
    res = client.get("/api/v1/projects/does-not-exist")
    assert res.status_code == 404
    err = res.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["message"]
    assert err["request_id"].startswith("req-")
    assert err["timestamp"]


def test_validation_error_is_400(client):
    res = client.post("/api/v1/projects", json={"name": "No location"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_domain_validation_error_is_400(client):
    """An out-of-enum category is a client error, not a 500."""
    project_id = client.post("/api/v1/projects", json={
        "name": "P", "project_type": "water", "country": "SA",
        "latitude": 1.0, "longitude": 1.0,
    }).json()["project_id"]
    res = client.post(f"/api/v1/projects/{project_id}/needs", json={
        "category": "not-a-category", "problem_statement": "x",
    })
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #
def test_create_and_get_project(client, project):
    pid = project["project_id"]
    body = client.get(f"/api/v1/projects/{pid}").json()
    assert body["name"] == "Al-Wadi Flood Protection"
    assert body["location"]["country"] == "SA"
    assert len(client.get("/api/v1/projects").json()["projects"]) >= 1


def test_patch_project_writes_audit_trail(client, project):
    pid = project["project_id"]
    res = client.patch(f"/api/v1/projects/{pid}", json={
        "description": "Revised scope", "reason": "Client change request",
    })
    assert res.status_code == 200
    assert res.json()["description"] == "Revised scope"

    entries = client.get(f"/api/v1/audit?entity_id={pid}").json()["entries"]
    assert any(e["action"] == "updated" and e["reason"] == "Client change request"
               for e in entries)
    update = next(e for e in entries if e["action"] == "updated")
    assert update["before"]["description"] == ""
    assert update["after"]["description"] == "Revised scope"


def test_unknown_project_type_is_assembly_error(client):
    res = client.post("/api/v1/projects", json={
        "name": "P", "project_type": "not-a-type", "country": "SA",
        "latitude": 1.0, "longitude": 1.0,
    })
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "ASSEMBLY_ERROR"


# --------------------------------------------------------------------------- #
# Site / need / ECP
# --------------------------------------------------------------------------- #
def test_site_and_need_registration(client, project):
    pid = project["project_id"]
    site = _make_site(client, pid)
    need = client.post(f"/api/v1/projects/{pid}/needs", json={
        "category": "safety", "problem_statement": "Protect residents",
        "affected_population_count": 10_000,
    })
    assert need.status_code == 201
    assert len(client.get(f"/api/v1/projects/{pid}/needs").json()["needs"]) == 1
    assert site["site_id"]


def test_assemble_ecp_populates_confidence_summary(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid, _make_site(client, pid)["site_id"])
    assert ecp["version"] == 1
    assert len(ecp["content_hash"]) == 64
    assert ecp["confidence_summary"]["average_confidence"] in list("ABCDE")
    assert [c["code_name"] for c in ecp["applicable_codes"]]


def test_ecp_assembly_is_idempotent_over_http(client, project):
    pid = project["project_id"]
    first = _make_ecp(client, pid)
    second = _make_ecp(client, pid)
    assert first["content_hash"] == second["content_hash"]
    assert first["version"] == second["version"] == 1


def test_ecp_requires_location(client, project):
    """Assembly is refused when the jurisdiction cascade has no anchor."""
    module = client.module
    project_id = project["project_id"]
    stored = module.cpo.get_project(project_id)
    stored.location = None
    res = client.post(f"/api/v1/projects/{project_id}/ecps")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "ASSEMBLY_ERROR"


# --------------------------------------------------------------------------- #
# Task lifecycle
# --------------------------------------------------------------------------- #
def _make_task(client, pid, ecp_id, **overrides):
    payload = {
        "project_id": pid, "ecp_id": ecp_id,
        "task_name": "Hydraulic analysis", "discipline": "civil",
    }
    payload.update(overrides)
    res = client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def test_task_lifecycle_happy_path(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    task = _make_task(client, pid, ecp["ecp_id"])

    assert client.post(f"/api/v1/tasks/{task['task_id']}/start").json()["status"] == "in_progress"
    assert client.post(f"/api/v1/tasks/{task['task_id']}/mark-under-review").json()["status"] == "under_review"
    assert client.post(f"/api/v1/tasks/{task['task_id']}/approve",
                       json={"approver_name": "Chief Reviewer"}).json()["status"] == "approved"
    assert client.post(f"/api/v1/tasks/{task['task_id']}/complete").json()["status"] == "completed"


def test_invalid_transition_is_409(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    task = _make_task(client, pid, ecp["ecp_id"])
    res = client.post(f"/api/v1/tasks/{task['task_id']}/complete")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "STATE_MACHINE_ERROR"


def test_reject_returns_task_to_ready(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    task = _make_task(client, pid, ecp["ecp_id"])
    client.post(f"/api/v1/tasks/{task['task_id']}/start")
    client.post(f"/api/v1/tasks/{task['task_id']}/mark-under-review")
    res = client.post(f"/api/v1/tasks/{task['task_id']}/reject",
                      json={"reason": "Calculation does not match hand check"})
    assert res.json()["status"] == "ready"
    log = client.get(f"/api/v1/tasks/{task['task_id']}").json()["execution_log"]
    assert any(e["event_type"] == "reject_task" for e in log)


# --------------------------------------------------------------------------- #
# Confidence gate & waivers
# --------------------------------------------------------------------------- #
def test_gate_blocks_level_e_and_returns_403_on_start(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    task = _make_task(client, pid, ecp["ecp_id"], assumptions=[
        {"assumption_text": "Groundwater level is 5.2 m", "confidence_level": "E"},
    ])

    gate = client.get(f"/api/v1/tasks/{task['task_id']}/gate").json()
    assert gate["can_proceed"] is False
    assert any("waiver" in i for i in gate["issues"])

    res = client.post(f"/api/v1/tasks/{task['task_id']}/start")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "GATE_BLOCKED"
    # The task is parked in `blocked` with its unblock conditions recorded.
    assert client.get(f"/api/v1/tasks/{task['task_id']}").json()["status"] == "blocked"


def test_waiver_unblocks_task(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    task = _make_task(client, pid, ecp["ecp_id"], assumptions=[
        {"assumption_text": "Groundwater level is 5.2 m", "confidence_level": "E"},
    ])
    res = client.post(f"/api/v1/tasks/{task['task_id']}/waiver", json={
        "parameter": "Groundwater level is 5.2 m",
        "rationale": "Regional studies indicate 5-6 m at 95% confidence.",
        "waived_by": "Chief Hydrogeologist",
    })
    assert res.status_code == 200
    gate = client.get(f"/api/v1/tasks/{task['task_id']}/gate").json()
    assert gate["can_proceed"] is True
    assert client.post(f"/api/v1/tasks/{task['task_id']}/start").status_code == 200


def test_safety_critical_task_refuses_waiver(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    task = _make_task(client, pid, ecp["ecp_id"], safety_critical=True, assumptions=[
        {"assumption_text": "PGA = 0.25g", "confidence_level": "E"},
    ])
    res = client.post(f"/api/v1/tasks/{task['task_id']}/waiver", json={
        "parameter": "PGA = 0.25g",
        "rationale": "Regional seismic assessment indicates conservative value.",
        "waived_by": "Structural Engineer",
    })
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "ASSEMBLY_ERROR"
    assert client.get(f"/api/v1/tasks/{task['task_id']}/gate").json()["can_proceed"] is False


def test_dependency_blocks_start_until_upstream_completes(client, project):
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    upstream = _make_task(client, pid, ecp["ecp_id"], task_name="Geotechnical survey")
    downstream = _make_task(client, pid, ecp["ecp_id"], task_name="Foundation design",
                            dependencies=[{"task_id": upstream["task_id"],
                                           "task_name": "Geotechnical survey"}])

    res = client.post(f"/api/v1/tasks/{downstream['task_id']}/start")
    assert res.status_code == 409
    assert "Geotechnical survey" in res.json()["error"]["message"]


def test_lag_days_is_enforced(client, project):
    """P1-S4-04: lag_days on a completed dependency still blocks the successor."""
    from datetime import datetime, timedelta, timezone

    module = client.module
    pid = project["project_id"]
    ecp = _make_ecp(client, pid)
    upstream = _make_task(client, pid, ecp["ecp_id"], task_name="Survey")
    client.post(f"/api/v1/tasks/{upstream['task_id']}/start")
    client.post(f"/api/v1/tasks/{upstream['task_id']}/mark-under-review")
    client.post(f"/api/v1/tasks/{upstream['task_id']}/approve")
    client.post(f"/api/v1/tasks/{upstream['task_id']}/complete")

    downstream = _make_task(client, pid, ecp["ecp_id"], task_name="Design",
                            dependencies=[{"task_id": upstream["task_id"], "lag_days": 3}])
    res = client.post(f"/api/v1/tasks/{downstream['task_id']}/start")
    assert res.status_code == 409
    assert "wait 3 day" in res.json()["error"]["message"]

    # Backdate completion past the lag and the successor may proceed.
    stored = module.cpo.get_task(upstream["task_id"])
    stored.completed_at = datetime.now(timezone.utc) - timedelta(days=4)
    assert client.post(f"/api/v1/tasks/{downstream['task_id']}/start").status_code == 200


# --------------------------------------------------------------------------- #
# Persistence, MCP surface, UI
# --------------------------------------------------------------------------- #
def test_registry_export_import_round_trip(client, project):
    exported = client.get("/api/v1/registry/export").json()
    assert exported["projects"]
    assert client.post("/api/v1/registry/import", json=exported).status_code == 200
    assert client.get("/api/v1/projects").json()["projects"]


def test_registry_import_rejects_garbage(client):
    res = client.post("/api/v1/registry/import", json={"projects": [{"name": "no type"}]})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_mcp_specification_exposes_tools(client):
    spec = client.get("/api/v1/mcp/specification").json()
    assert spec["name"] == "mcp-project"
    for tool in ("create_project", "register_site", "assemble_ecp", "create_task", "check_gate"):
        assert tool in spec["tools"]


def test_ui_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "CIVIL-OS" in res.text
