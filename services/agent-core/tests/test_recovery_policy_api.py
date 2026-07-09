"""Integration tests for Recovery Policy API endpoint."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_recovery_policy_endpoint_returns_200(client):
    """GET /recovery-policy returns 200."""
    response = await client.get("/recovery-policy")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_recovery_policy_has_required_fields(client):
    """Result contains scenarios, categories, total, disclaimer."""
    response = await client.get("/recovery-policy")
    data = response.json()
    assert "scenarios" in data
    assert "categories" in data
    assert "total" in data
    assert "disclaimer" in data


@pytest.mark.anyio
async def test_recovery_policy_is_read_only(client):
    """Multiple GET returns consistent results."""
    r1 = await client.get("/recovery-policy")
    r2 = await client.get("/recovery-policy")
    assert r1.json() == r2.json()


@pytest.mark.anyio
async def test_session_recovery_embeds_real_recovery_policy(client):
    """Session recovery should expose the same structured policy, not an empty fallback."""
    response = await client.get("/session-recovery")
    assert response.status_code == 200
    policy = response.json()["recovery_policy"]
    assert "scenarios" in policy
    assert "categories" in policy
    assert "total" in policy
    assert policy["total"] > 0
