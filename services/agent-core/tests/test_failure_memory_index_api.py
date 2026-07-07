"""Tests for Failure Memory Index API endpoints."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── GET /failures ───────────────────────────────────────────────────────

def test_list_failures_returns_200(client):
    resp = client.get("/failures")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_failures_has_required_fields(client):
    resp = client.get("/failures")
    data = resp.json()
    for item in data:
        assert "failure_id" in item
        assert "category" in item
        assert "severity" in item
        assert "milestone" in item
        assert "symptom_cn" in item
        assert "source_refs" in item


def test_list_failures_filter_by_category(client):
    resp = client.get("/failures?category=code_quality")
    assert resp.status_code == 200
    data = resp.json()
    for item in data:
        assert "code_quality" in item["category"]


def test_list_failures_filter_by_severity(client):
    resp = client.get("/failures?severity=P1")
    assert resp.status_code == 200
    data = resp.json()
    for item in data:
        assert item["severity"] == "P1"


# ── GET /failures/summary ───────────────────────────────────────────────

def test_failures_summary(client):
    resp = client.get("/failures/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_failures" in data
    assert "category_distribution" in data
    assert "severity_distribution" in data


def test_failures_summary_note_chinese(client):
    resp = client.get("/failures/summary")
    data = resp.json()
    assert "只读" in data["note"]


# ── GET /failures/query/by-keyword ──────────────────────────────────────

def test_query_by_keyword(client):
    resp = client.get("/failures/query/by-keyword?keyword=修复")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_query_by_keyword_no_results(client):
    resp = client.get("/failures/query/by-keyword?keyword=xyznonexistent12345")
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


def test_query_by_keyword_missing_param(client):
    resp = client.get("/failures/query/by-keyword")
    assert resp.status_code == 422


# ── GET /failures/{failure_id} ──────────────────────────────────────────

def test_get_failure_detail(client):
    # First list to get an ID
    list_resp = client.get("/failures")
    items = list_resp.json()
    if items:
        first_id = items[0]["failure_id"]
        resp = client.get(f"/failures/{first_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["failure_id"] == first_id


def test_get_failure_404(client):
    resp = client.get("/failures/nonexistent-id")
    assert resp.status_code == 404


# ── Read-only verification ──────────────────────────────────────────────

def test_no_post_endpoint(client):
    resp = client.post("/failures", json={})
    assert resp.status_code == 405


def test_no_put_endpoint(client):
    resp = client.put("/failures/some-id", json={})
    assert resp.status_code == 405


def test_no_delete_endpoint(client):
    resp = client.delete("/failures/some-id")
    assert resp.status_code == 405
