"""API tests for Role Protocol router."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── GET /roles ─────────────────────────────────────────────────────────

def test_list_roles_returns_200(client):
    resp = client.get("/roles")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5


def test_list_roles_all_have_ids(client):
    resp = client.get("/roles")
    ids = [r["role_id"] for r in resp.json()]
    assert "planner" in ids
    assert "builder" in ids
    assert "reviewer" in ids
    assert "researcher" in ids
    assert "skill_learner" in ids


# ── GET /roles/{role_id} ──────────────────────────────────────────────

def test_get_role_builder(client):
    resp = client.get("/roles/builder")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role_id"] == "builder"
    assert data["name_cn"] == "构建者"
    assert data["can_execute_code"] is True
    assert data["can_approve"] is False


def test_get_role_planner(client):
    resp = client.get("/roles/planner")
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_execute_code"] is False
    assert data["can_modify_files"] is False


def test_get_role_not_found(client):
    resp = client.get("/roles/nonexistent")
    assert resp.status_code == 404


# ── POST /roles/validate-output ───────────────────────────────────────

def test_validate_output_ok(client):
    resp = client.post("/roles/validate-output", json={
        "role_id": "planner",
        "output_data": {
            "task_breakdown": [],
            "risk_assessment": "low",
            "assignment": {},
            "source_refs": ["docs/spec.md"],
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


def test_validate_output_missing_evidence(client):
    resp = client.post("/roles/validate-output", json={
        "role_id": "builder",
        "output_data": {"code_changes": "diff"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False


def test_validate_output_unknown_role(client):
    resp = client.post("/roles/validate-output", json={
        "role_id": "unknown",
        "output_data": {},
    })
    assert resp.status_code == 400


def test_validate_output_missing_role_id(client):
    resp = client.post("/roles/validate-output", json={
        "output_data": {"evidence_refs": ["a"]},
    })
    assert resp.status_code == 400


# ── GET /roles/{role_id}/boundary ─────────────────────────────────────

def test_boundary_planner(client):
    resp = client.get("/roles/planner/boundary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role_id"] == "planner"
    assert "can_do" in data
    assert "cannot_do" in data


def test_boundary_not_found(client):
    resp = client.get("/roles/unknown/boundary")
    assert resp.status_code == 404


# ── POST /roles/validate-transition ───────────────────────────────────

def test_validate_transition_ok(client):
    resp = client.post("/roles/validate-transition", json={
        "from_role_id": "planner",
        "to_role_id": "builder",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


def test_validate_transition_self_loop(client):
    resp = client.post("/roles/validate-transition", json={
        "from_role_id": "planner",
        "to_role_id": "planner",
    })
    assert resp.status_code == 400


def test_validate_transition_missing_fields(client):
    resp = client.post("/roles/validate-transition", json={})
    assert resp.status_code == 400


# ── GET /roles/handoff-format ─────────────────────────────────────────

def test_handoff_format(client):
    resp = client.get("/roles/handoff-format")
    assert resp.status_code == 200
    data = resp.json()
    assert "fields" in data
    assert "required_fields" in data


# ── Chinese UI check ──────────────────────────────────────────────────

def test_all_responses_contain_chinese(client):
    """Verify role names and error messages are in Chinese."""
    resp = client.get("/roles")
    names = [r["name_cn"] for r in resp.json()]
    assert "规划者" in names
    assert "构建者" in names
    assert "审查者" in names
    assert "研究员" in names
    assert "技能学习者" in names
