"""Integration tests for Safe Retry Loop API."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_assess_retryable(client):
    """POST assess with network_failure returns allowed."""
    r = await client.post("/retry/assess", json={
        "failure_category": "network_failure", "attempt": 0, "max_attempts": 3,
    })
    assert r.status_code == 200
    assert r.json()["allowed"] is True


@pytest.mark.anyio
async def test_assess_security_block_denied(client):
    """POST assess with security_block returns not allowed."""
    r = await client.post("/retry/assess", json={
        "failure_category": "security_block", "attempt": 0, "max_attempts": 3,
    })
    assert r.status_code == 200
    assert r.json()["allowed"] is False


@pytest.mark.anyio
async def test_assess_max_attempts_exceeded(client):
    """POST assess with exceeded attempts returns not allowed."""
    r = await client.post("/retry/assess", json={
        "failure_category": "network_failure", "attempt": 3, "max_attempts": 3,
    })
    assert r.status_code == 200
    assert r.json()["allowed"] is False


@pytest.mark.anyio
async def test_assess_dangerous_tool(client):
    """POST assess with dangerous tool returns not allowed."""
    r = await client.post("/retry/assess", json={
        "failure_category": "tool_failure", "tool_names": ["git_push"],
        "attempt": 0, "max_attempts": 3,
    })
    assert r.status_code == 200
    assert r.json()["allowed"] is False


@pytest.mark.anyio
async def test_record_retry(client):
    """POST record returns decision with history."""
    r = await client.post("/retry/record", json={
        "failure_category": "network_failure", "error_text": "timeout",
    })
    assert r.status_code == 200
    data = r.json()
    assert "history" in data
    assert len(data["history"]) == 1


@pytest.mark.anyio
async def test_assess_missing_category_fails(client):
    """POST assess without failure_category returns 400."""
    r = await client.post("/retry/assess", json={"attempt": 0})
    assert r.status_code == 400
