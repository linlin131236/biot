"""Tests for User Preference Memory API."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── GET /preferences ────────────────────────────────────────────────────

def test_list_preferences_returns_200(client):
    resp = client.get("/preferences")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 10


def test_list_preferences_has_required_fields(client):
    resp = client.get("/preferences")
    for item in resp.json():
        assert "preference_id" in item
        assert "category" in item
        assert "statement_cn" in item
        assert "confidence" in item
        assert "source_refs" in item
        assert "can_apply_automatically" in item
        assert "requires_confirmation" in item


def test_list_preferences_filter_by_category(client):
    resp = client.get("/preferences?category=safety")
    assert resp.status_code == 200
    for item in resp.json():
        assert item["category"] == "safety"


# ── GET /preferences/summary ────────────────────────────────────────────

def test_preferences_summary(client):
    resp = client.get("/preferences/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_preferences" in data
    assert "category_distribution" in data
    assert "auto_apply_count" in data
    assert data["total_preferences"] >= 10


def test_preferences_summary_note_chinese(client):
    resp = client.get("/preferences/summary")
    assert "只读" in resp.json()["note"]


# ── GET /preferences/{preference_id} ────────────────────────────────────

def test_get_preference_detail(client):
    resp = client.get("/preferences/pref-001-language")
    assert resp.status_code == 200
    data = resp.json()
    assert data["preference_id"] == "pref-001-language"
    assert "中文" in data["statement_cn"]


def test_get_preference_404(client):
    resp = client.get("/preferences/nonexistent")
    assert resp.status_code == 404


# ── GET /preferences/query/by-keyword ───────────────────────────────────

def test_query_by_keyword(client):
    resp = client.get("/preferences/query/by-keyword?keyword=安全")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


def test_query_by_keyword_no_results(client):
    resp = client.get("/preferences/query/by-keyword?keyword=xyz12345")
    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /preferences/check/conflicts ────────────────────────────────────

def test_check_conflicts(client):
    resp = client.get("/preferences/check/conflicts")
    assert resp.status_code == 200
    data = resp.json()
    assert "has_conflicts" in data
    assert "conflicts" in data


# ── GET /preferences/check/secret ───────────────────────────────────────

def test_check_secret_detected(client):
    resp = client.get("/preferences/check/secret?text=sk-abc123def456ghi789jkl012mno345pqr678")
    assert resp.status_code == 200
    assert resp.json()["contains_secret_pattern"] is True


def test_check_secret_not_detected(client):
    resp = client.get("/preferences/check/secret?text=所有UI必须中文")
    assert resp.status_code == 200
    assert resp.json()["contains_secret_pattern"] is False


# ── Read-only verification ──────────────────────────────────────────────

def test_no_post_endpoint(client):
    resp = client.post("/preferences", json={})
    assert resp.status_code == 405


def test_no_put_endpoint(client):
    resp = client.put("/preferences/pref-001-language", json={})
    assert resp.status_code == 405


def test_no_delete_endpoint(client):
    resp = client.delete("/preferences/pref-001-language")
    assert resp.status_code == 405
