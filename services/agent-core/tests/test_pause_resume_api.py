"""Integration tests for Pause/Resume API."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_pause_node(client):
    """POST pause succeeds for running node."""
    r = await client.post("/pause-resume/pause", json={
        "node_id": "n1", "current_status": "running", "reason": "需要检查",
    })
    assert r.status_code == 200
    assert r.json()["action"] == "paused"


@pytest.mark.anyio
async def test_resume_node(client):
    """POST resume returns checks with human decision required."""
    await client.post("/pause-resume/pause", json={
        "node_id": "n2", "current_status": "running",
    })
    r = await client.post("/pause-resume/resume", json={"node_id": "n2"})
    assert r.status_code == 200
    assert r.json()["action"] == "resumed"
    assert r.json()["requires_human_decision"] is True


@pytest.mark.anyio
async def test_cancel_pause(client):
    """POST cancel marks node as failed."""
    await client.post("/pause-resume/pause", json={
        "node_id": "n3", "current_status": "running",
    })
    r = await client.post("/pause-resume/cancel", json={"node_id": "n3"})
    assert r.status_code == 200
    assert r.json()["to_status"] == "failed"


@pytest.mark.anyio
async def test_pause_status(client):
    """GET status returns is_paused and snapshot."""
    await client.post("/pause-resume/pause", json={
        "node_id": "n4", "current_status": "running",
    })
    r = await client.get("/pause-resume/status/n4")
    assert r.status_code == 200
    assert r.json()["is_paused"] is True
    assert r.json()["snapshot"] is not None


@pytest.mark.anyio
async def test_list_paused(client):
    """GET paused lists all paused nodes."""
    await client.post("/pause-resume/pause", json={
        "node_id": "n5", "current_status": "running",
    })
    r = await client.get("/pause-resume/paused")
    assert r.status_code == 200
    assert "n5" in r.json()["paused_nodes"]


@pytest.mark.anyio
async def test_pause_invalid_status(client):
    """Pause from invalid status returns 400."""
    r = await client.post("/pause-resume/pause", json={
        "node_id": "n6", "current_status": "completed",
    })
    assert r.status_code == 400


@pytest.mark.anyio
async def test_resume_not_paused(client):
    """Resume non-paused node returns 400."""
    r = await client.post("/pause-resume/resume", json={"node_id": "never_paused"})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_resume_recheck_permissions_false_blocked(client):
    """Resume with recheck_permissions=false returns 400 — cannot skip."""
    await client.post("/pause-resume/pause", json={
        "node_id": "n_perm", "current_status": "running",
    })
    r = await client.post("/pause-resume/resume", json={
        "node_id": "n_perm", "recheck_permissions": False,
    })
    assert r.status_code == 400
    assert "权限" in r.json()["detail"] or "不可跳过" in r.json()["detail"]
