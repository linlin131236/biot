"""Integration tests for Local Release Checklist API endpoint."""
import subprocess

import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    """Create a test client with a minimal project dir containing git and docs."""
    proj = tmp_path / "proj"
    proj.mkdir()
    subprocess.run(["git", "init"], cwd=str(proj), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(proj), capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(proj), capture_output=True)
    docs = proj / "docs"
    docs.mkdir(parents=True)
    (docs / "project-state.md").write_text("# Bolt Project State\n- 已完成到：M57", encoding="utf-8")
    (docs / "phase-57-review-gate.md").write_text("## 状态", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(proj), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(proj), capture_output=True)
    audit_path = tmp_path / "execution-audit.json"
    app = create_app(execution_audit_path=audit_path, project_dir=str(proj))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_checklist_endpoint_returns_200(client):
    """GET /local-release-checklist returns 200."""
    response = await client.get("/local-release-checklist")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_checklist_endpoint_has_required_fields(client):
    """Result contains ready, items, blockers, warnings, next_step, disclaimer."""
    response = await client.get("/local-release-checklist")
    data = response.json()
    assert "ready" in data
    assert "items" in data
    assert "blockers" in data
    assert "warnings" in data
    assert "next_step" in data
    assert "disclaimer" in data


@pytest.mark.anyio
async def test_checklist_endpoint_is_read_only(client):
    """Multiple GET returns consistent results."""
    r1 = await client.get("/local-release-checklist")
    r2 = await client.get("/local-release-checklist")
    assert r1.json() == r2.json()
