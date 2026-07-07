"""Integration tests for Planner Task Graph API endpoints."""
import httpx
import pytest

from bolt_core.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(execution_audit_path=tmp_path / "audit.json", project_dir=str(tmp_path))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_create_and_list_graphs(client):
    """POST create + GET list returns the created graph."""
    r = await client.post("/planner/graphs", json={"title": "测试任务", "objective": "验证任务图"})
    assert r.status_code == 200
    g = r.json()
    assert g["id"].startswith("graph_")

    r2 = await client.get("/planner/graphs")
    assert r2.status_code == 200
    summaries = r2.json()
    assert len(summaries) >= 1
    assert summaries[0]["title"] == "测试任务"


@pytest.mark.anyio
async def test_get_graph_by_id(client):
    """GET /planner/graphs/{id} returns full graph with nodes."""
    r = await client.post("/planner/graphs", json={"title": "测试", "objective": "目标"})
    gid = r.json()["id"]
    await client.post(f"/planner/graphs/{gid}/nodes", json={"title": "节点A"})

    r2 = await client.get(f"/planner/graphs/{gid}")
    assert r2.status_code == 200
    data = r2.json()
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["title"] == "节点A"


@pytest.mark.anyio
async def test_create_graph_without_title_fails(client):
    """POST without title returns 400."""
    r = await client.post("/planner/graphs", json={"objective": "目标"})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_add_node_with_dependency(client):
    """Node with dependency can be added and started after dep completes."""
    r = await client.post("/planner/graphs", json={"title": "测试", "objective": "目标"})
    gid = r.json()["id"]

    n1 = await client.post(f"/planner/graphs/{gid}/nodes", json={"title": "前置"})
    n1id = n1.json()["id"]

    n2 = await client.post(f"/planner/graphs/{gid}/nodes", json={"title": "后置", "dependencies": [n1id]})
    assert n2.status_code == 200

    # Cannot start n2 before n1 is completed
    r3 = await client.patch(f"/planner/graphs/{gid}/nodes/{n2.json()['id']}", json={"status": "in_progress"})
    assert r3.status_code == 400
    assert "不" in r3.json()["detail"] or "not completed" in r3.json()["detail"]


@pytest.mark.anyio
async def test_update_node_invalid_transition(client):
    """Invalid status transition returns 400."""
    r = await client.post("/planner/graphs", json={"title": "测试", "objective": "目标"})
    gid = r.json()["id"]
    n = await client.post(f"/planner/graphs/{gid}/nodes", json={"title": "节点"})
    nid = n.json()["id"]

    # pending -> completed is not allowed
    r2 = await client.patch(f"/planner/graphs/{gid}/nodes/{nid}", json={"status": "completed"})
    assert r2.status_code == 400


@pytest.mark.anyio
async def test_get_nonexistent_graph_returns_404(client):
    """GET non-existent graph returns 404."""
    r = await client.get("/planner/graphs/nonexistent")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_planner_graph_is_read_only_list(client):
    """GET /planner/graphs is read-only and returns consistent results."""
    r1 = await client.get("/planner/graphs")
    r2 = await client.get("/planner/graphs")
    assert r1.json() == r2.json()
