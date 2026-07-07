"""Tests for Memory Permission Boundary API."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── POST /memory-permission/classify ────────────────────────────────────

def test_classify_secret_content(client):
    resp = client.post("/memory-permission/classify", json={
        "content": "sk-abc123def456ghi789jkl012mno345pqr678stu",
        "source": "user input",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "secret"
    assert data["can_read"] is False
    assert data["can_write"] is False


def test_classify_public_content(client):
    resp = client.post("/memory-permission/classify", json={
        "content": "Bolt 项目信息",
        "source": "docs/project-state.md",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_read"] is True


def test_classify_sensitive_content(client):
    resp = client.post("/memory-permission/classify", json={
        "content": "password: mysecret123",
        "source": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] in ("sensitive", "secret")


# ── GET /memory-permission/tiers ────────────────────────────────────────

def test_list_tiers(client):
    resp = client.get("/memory-permission/tiers")
    assert resp.status_code == 200
    data = resp.json()
    assert "tiers" in data
    assert len(data["tiers"]) == 7  # 7 tiers


def test_list_tiers_has_secret_blocked(client):
    resp = client.get("/memory-permission/tiers")
    tiers = resp.json()["tiers"]
    secret = [t for t in tiers if t["tier"] == "secret"]
    assert len(secret) == 1
    assert secret[0]["can_read"] is False
    assert secret[0]["can_write"] is False


# ── POST /memory-permission/check-write ─────────────────────────────────

def test_check_write_blocks_secret(client):
    resp = client.post("/memory-permission/check-write", json={
        "content": "sk-abc123def456ghi789jkl012mno345pqr678stu",
        "source": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is True
    assert data["can_write"] is False


def test_check_write_allows_public(client):
    resp = client.post("/memory-permission/check-write", json={
        "content": "Bolt 项目技术栈：Python + TypeScript + Electron",
        "source": "docs/project-state.md",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is False
    assert data["can_write"] is True


# ── Read-only check ─────────────────────────────────────────────────────

def test_tiers_is_read_only(client):
    resp = client.post("/memory-permission/tiers", json={})
    assert resp.status_code == 405
