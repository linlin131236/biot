"""Integration tests for Failure Classifier API."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_categories_returns_200(client):
    """GET /failure/categories returns 200."""
    r = await client.get("/failure/categories")
    assert r.status_code == 200
    data = r.json()
    assert "user_input" in data
    assert "security_block" in data


@pytest.mark.anyio
async def test_classify_network_error(client):
    """POST classify with network error returns network_failure."""
    r = await client.post("/failure/classify", json={"error": "ConnectionError: timeout"})
    assert r.status_code == 200
    assert r.json()["category"] == "network_failure"


@pytest.mark.anyio
async def test_classify_permission_denied(client):
    """POST classify with permission denied returns security_block."""
    r = await client.post("/failure/classify", json={"error": "permission denied"})
    assert r.status_code == 200
    assert r.json()["category"] == "security_block"


@pytest.mark.anyio
async def test_classify_empty_error_fails(client):
    """POST classify with empty error returns 400."""
    r = await client.post("/failure/classify", json={"error": ""})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_is_retryable(client):
    """POST is-retryable returns correct result."""
    r = await client.post("/failure/is-retryable", json={"error": "timeout"})
    assert r.status_code == 200
    assert r.json()["retryable"] is True
