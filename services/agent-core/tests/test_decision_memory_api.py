"""Tests for Decision Memory API endpoints."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── GET /decisions ─────────────────────────────────────────────────────

def test_list_decisions_returns_200(client):
    resp = client.get("/decisions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 60, f"Expected ≥60 decisions, got {len(data)}"


def test_list_decisions_has_required_fields(client):
    resp = client.get("/decisions")
    data = resp.json()
    for item in data:
        assert "decision_id" in item
        assert "milestone" in item
        assert "title" in item
        assert "summary_cn" in item
        assert "source_refs" in item


def test_list_decisions_filter_by_milestone(client):
    resp = client.get("/decisions?milestone=M70")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    for item in data:
        assert "M70" in item["milestone"] or "70" in str(item)


# ── GET /decisions/{decision_id} ───────────────────────────────────────

def test_get_decision_detail(client):
    resp = client.get("/decisions/072-code-map-index")
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision_id"] == "072-code-map-index"
    assert data["title"] != ""
    assert data["summary_cn"] != ""
    assert data["rationale"] != ""
    assert len(data["source_refs"]) >= 1


def test_get_decision_404(client):
    resp = client.get("/decisions/nonexistent-id")
    assert resp.status_code == 404
    assert "未找到" in resp.json()["detail"]


def test_get_decision_m71(client):
    resp = client.get("/decisions/071-project-profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["milestone"] == "M71"


def test_get_decision_m70(client):
    resp = client.get("/decisions/070-agent-workflow-beta")
    assert resp.status_code == 200


# ── GET /decisions/query/by-keyword ────────────────────────────────────

def test_query_by_keyword(client):
    resp = client.get("/decisions/query/by-keyword?keyword=安全")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_query_by_keyword_no_results(client):
    resp = client.get("/decisions/query/by-keyword?keyword=xyznonexistent12345")
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


def test_query_by_keyword_missing_param(client):
    resp = client.get("/decisions/query/by-keyword")
    assert resp.status_code == 422  # FastAPI validation error


# ── GET /decisions/summary ─────────────────────────────────────────────

def test_decisions_summary(client):
    resp = client.get("/decisions/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_decisions" in data
    assert "milestone_distribution" in data
    assert data["total_decisions"] >= 60
    assert isinstance(data["milestone_distribution"], dict)


def test_decisions_summary_note_is_chinese(client):
    resp = client.get("/decisions/summary")
    data = resp.json()
    assert "只读" in data["note"]


# ── All endpoints: no auto-execution ──────────────────────────────────

def test_no_post_endpoint_for_decisions(client):
    """Decision memory is read-only - no POST endpoints."""
    resp = client.post("/decisions", json={})
    assert resp.status_code == 405  # Method Not Allowed


def test_no_put_endpoint_for_decisions(client):
    resp = client.put("/decisions/072-code-map-index", json={})
    assert resp.status_code == 405


def test_no_delete_endpoint_for_decisions(client):
    resp = client.delete("/decisions/072-code-map-index")
    assert resp.status_code == 405
