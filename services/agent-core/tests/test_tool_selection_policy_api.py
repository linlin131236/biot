"""Integration tests for Tool Selection Policy API."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_summary_returns_200(client):
    """GET /tools/policy/summary returns 200."""
    r = await client.get("/tools/policy/summary")
    assert r.status_code == 200
    data = r.json()
    assert "classes" in data
    assert "total" in data


@pytest.mark.anyio
async def test_classify_read_only(client):
    """Classify a read-only tool."""
    r = await client.get("/tools/policy/classify/read_file")
    assert r.status_code == 200
    assert r.json()["class"] == "read_only"


@pytest.mark.anyio
async def test_classify_unknown(client):
    """Classify an unknown tool returns unknown."""
    r = await client.get("/tools/policy/classify/fake_tool")
    assert r.status_code == 200
    assert r.json()["class"] == "unknown"


@pytest.mark.anyio
async def test_list_tools(client):
    """List all tools."""
    r = await client.get("/tools/policy/list")
    assert r.status_code == 200
    assert len(r.json()) > 10


@pytest.mark.anyio
async def test_list_dangerous_tools(client):
    """List dangerous tools only."""
    r = await client.get("/tools/policy/list?tool_class=dangerous")
    assert r.status_code == 200
    for t in r.json():
        assert t["class"] == "dangerous"


@pytest.mark.anyio
async def test_select_tools_validation(client):
    """POST select validates tool selection."""
    r = await client.post("/tools/policy/select", json={
        "tools": ["read_file", "git_push"], "reason": "测试选择"
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 2
    assert data["any_requires_permission"] is True


@pytest.mark.anyio
async def test_select_empty_tools_fails(client):
    """POST select with empty tools returns 400."""
    r = await client.post("/tools/policy/select", json={"tools": []})
    assert r.status_code == 400
