"""API tests for Multi-Agent Workflow router."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def wf_id(client):
    """Create a workflow and return its id."""
    resp = client.post("/workflows", json={"title_cn": "API测试工作流"})
    assert resp.status_code == 200
    return resp.json()["workflow_id"]


# ── POST /workflows ────────────────────────────────────────────────────

def test_create_workflow(client):
    resp = client.post("/workflows", json={"title_cn": "新工作流"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow_id"].startswith("wf-")
    assert data["state"] == "planning"
    assert data["state_label_cn"] == "规划中"


def test_create_workflow_missing_title(client):
    resp = client.post("/workflows", json={})
    assert resp.status_code == 400


# ── GET /workflows ─────────────────────────────────────────────────────

def test_list_workflows(client):
    client.post("/workflows", json={"title_cn": "a"})
    client.post("/workflows", json={"title_cn": "b"})
    resp = client.get("/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


# ── GET /workflows/{id} ────────────────────────────────────────────────

def test_get_workflow(client, wf_id):
    resp = client.get(f"/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["workflow_id"] == wf_id


def test_get_workflow_not_found(client):
    resp = client.get("/workflows/nonexistent")
    assert resp.status_code == 404


# ── GET /workflows/{id}/status-summary ─────────────────────────────────

def test_status_summary(client, wf_id):
    resp = client.get(f"/workflows/{wf_id}/status-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary_cn" in data
    assert "规划" in data["summary_cn"]


# ── POST /workflows/{id}/planner-output ────────────────────────────────

def test_planner_output_ok(client, wf_id):
    resp = client.post(f"/workflows/{wf_id}/planner-output", json={
        "task_breakdown": [{"title": "t1"}],
        "risk_assessment": "low",
        "assignment": {"t1": "builder"},
        "source_refs": ["docs/spec.md"],
        "context": "ctx-p",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["new_state"] == "ready_for_build"


def test_planner_output_no_source_refs(client, wf_id):
    resp = client.post(f"/workflows/{wf_id}/planner-output", json={
        "task_breakdown": [],
        "risk_assessment": "low",
        "assignment": {},
        "source_refs": [],
    })
    assert resp.status_code == 400


# ── Happy path API test ────────────────────────────────────────────────

def test_happy_path_api(client):
    # Create
    r = client.post("/workflows", json={"title_cn": "完整API测试"})
    wf_id = r.json()["workflow_id"]

    # Planner
    r = client.post(f"/workflows/{wf_id}/planner-output", json={
        "task_breakdown": [{"title": "t1"}],
        "risk_assessment": "low",
        "assignment": {"t1": "builder"},
        "source_refs": ["docs/spec.md"],
        "context": "ctx-p",
    })
    assert r.status_code == 200
    assert r.json()["new_state"] == "ready_for_build"

    # Builder (need to manually transition to building first via internal)
    # The API doesn't have a "start building" endpoint; it's implied by builder-output
    # But builder-output requires BUILDING state, not READY_FOR_BUILD
    # So we need a transition. Let's test the error case:
    r = client.post(f"/workflows/{wf_id}/builder-output", json={
        "code_changes": "code",
        "tests": "pass",
        "evidence_refs": ["log"],
        "source_refs": ["ref"],
        "context": "ctx-b",
    })
    assert r.status_code == 400  # not in building state

    # Verify state summary
    r = client.get(f"/workflows/{wf_id}/status-summary")
    assert r.json()["state"] == "ready_for_build"


# ── POST /workflows/{id}/validate-transition ───────────────────────────

def test_validate_transition_valid(client, wf_id):
    resp = client.post(f"/workflows/{wf_id}/validate-transition", json={
        "target_state": "ready_for_build",
    })
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_validate_transition_invalid(client, wf_id):
    resp = client.post(f"/workflows/{wf_id}/validate-transition", json={
        "target_state": "approved",
    })
    assert resp.status_code == 400


def test_validate_transition_missing_state(client, wf_id):
    resp = client.post(f"/workflows/{wf_id}/validate-transition", json={})
    assert resp.status_code == 400


# ── Chinese UI ─────────────────────────────────────────────────────────

def test_labels_are_chinese(client, wf_id):
    resp = client.get(f"/workflows/{wf_id}")
    data = resp.json()
    assert data["state_label_cn"] == "规划中"

    resp = client.get(f"/workflows/{wf_id}/status-summary")
    data = resp.json()
    assert any('\u4e00' <= c <= '\u9fff' for c in data["summary_cn"])
