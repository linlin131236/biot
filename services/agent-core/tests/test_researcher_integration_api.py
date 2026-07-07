"""API tests for Researcher Integration router."""
import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── GET /research/scopes ──────────────────────────────────────────────

def test_list_scopes(client):
    resp = client.get("/research/scopes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5


# ── POST /research/briefs ─────────────────────────────────────────────

def test_create_brief_ok(client):
    resp = client.post("/research/briefs", json={
        "title_cn": "研究测试",
        "question_cn": "研究什么问题?",
        "allowed_sources": ["doc1.md", "doc2.md"],
        "scope": "project_docs",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["brief_id"].startswith("rb-")
    assert data["scope_label_cn"] == "项目文档"


def test_create_brief_too_many_sources(client):
    resp = client.post("/research/briefs", json={
        "title_cn": "test",
        "question_cn": "q",
        "allowed_sources": ["a", "b", "c", "d", "e"],
        "scope": "project_docs",
    })
    assert resp.status_code == 400


def test_create_brief_invalid_scope(client):
    resp = client.post("/research/briefs", json={
        "title_cn": "test",
        "question_cn": "q",
        "allowed_sources": ["a", "b"],
        "scope": "invalid",
    })
    assert resp.status_code == 400


# ── GET /research/briefs ──────────────────────────────────────────────

def test_list_briefs(client):
    client.post("/research/briefs", json={
        "title_cn": "a", "question_cn": "q",
        "allowed_sources": ["d1", "d2"], "scope": "code_map",
    })
    resp = client.get("/research/briefs")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── POST /research/summaries ──────────────────────────────────────────

def test_produce_summary_ok(client):
    r = client.post("/research/briefs", json={
        "title_cn": "t", "question_cn": "q",
        "allowed_sources": ["d1.md", "d2.md"], "scope": "decision_memory",
    })
    brief_id = r.json()["brief_id"]

    resp = client.post("/research/summaries", json={
        "brief_id": brief_id,
        "summary_cn": "中文摘要",
        "principles_cn": ["原则1"],
        "risks_cn": ["风险1"],
        "source_refs": ["d1.md", "d2.md"],
    })
    assert resp.status_code == 200
    assert resp.json()["summary_cn"] == "中文摘要"


def test_produce_summary_no_source_refs(client):
    r = client.post("/research/briefs", json={
        "title_cn": "t", "question_cn": "q",
        "allowed_sources": ["d1.md", "d2.md"], "scope": "decision_memory",
    })
    brief_id = r.json()["brief_id"]

    resp = client.post("/research/summaries", json={
        "brief_id": brief_id,
        "summary_cn": "摘要",
        "principles_cn": [],
        "risks_cn": [],
        "source_refs": [],
    })
    assert resp.status_code == 400


# ── POST /research/validate-source-refs ───────────────────────────────

def test_validate_source_refs(client):
    resp = client.post("/research/validate-source-refs", json={
        "source_refs": ["doc1.md"],
    })
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


# ── Chinese UI ────────────────────────────────────────────────────────

def test_scopes_chinese(client):
    resp = client.get("/research/scopes")
    labels = [s["label_cn"] for s in resp.json()]
    assert "项目文档" in labels
    assert "决策记忆" in labels
