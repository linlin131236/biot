"""Integration tests for Execution State Machine API."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_state_machine_summary_returns_200(client):
    """GET /execution/state-machine/summary returns 200."""
    r = await client.get("/execution/state-machine/summary")
    assert r.status_code == 200
    data = r.json()
    assert "states" in data
    assert "transitions" in data
    assert "terminal" in data


@pytest.mark.anyio
async def test_allowed_transitions_from_pending(client):
    """GET transitions from pending returns ready and blocked."""
    r = await client.get("/execution/state-machine/transitions/pending")
    assert r.status_code == 200
    data = r.json()
    assert "ready" in data["allowed"]
    assert "blocked" in data["allowed"]
    assert data["is_terminal"] is False


@pytest.mark.anyio
async def test_allowed_transitions_from_completed(client):
    """GET transitions from completed returns empty (terminal)."""
    r = await client.get("/execution/state-machine/transitions/completed")
    assert r.status_code == 200
    data = r.json()
    assert data["allowed"] == []
    assert data["is_terminal"] is True


@pytest.mark.anyio
async def test_validate_valid_transition(client):
    """POST validate with valid transition returns valid: true."""
    r = await client.post("/execution/state-machine/validate", json={
        "from_state": "pending", "to_state": "ready", "node_id": "n1"
    })
    assert r.status_code == 200
    assert r.json()["valid"] is True


@pytest.mark.anyio
async def test_validate_invalid_transition(client):
    """POST validate with invalid transition returns 400."""
    r = await client.post("/execution/state-machine/validate", json={
        "from_state": "completed", "to_state": "running"
    })
    assert r.status_code == 400


@pytest.mark.anyio
async def test_validate_unknown_state(client):
    """POST validate with unknown state returns 400."""
    r = await client.post("/execution/state-machine/validate", json={
        "from_state": "pending", "to_state": "unknown"
    })
    assert r.status_code == 400


@pytest.mark.anyio
async def test_allowed_transitions_unknown_state(client):
    """GET transitions from unknown state returns 400."""
    r = await client.get("/execution/state-machine/transitions/unknown")
    assert r.status_code == 400
