"""Tests for task closure API endpoints via ASGI test client."""
import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.anyio
async def test_get_task_templates(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/task-closures/templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) == 5
        assert templates[0]["id"] == "bugfix"
        assert templates[0]["label"] == "修复小问题"


@pytest.mark.anyio
async def test_create_task_closure(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/task-closures", json={
            "objective": "修复 README 拼写错误",
            "template_id": "docs",
            "run_id": "run_1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["objective"] == "修复 README 拼写错误"
        assert data["template_id"] == "docs"
        assert data["status"] == "pending"
        assert data["final_status"] == "pending"
        assert data["run_id"] == "run_1"


@pytest.mark.anyio
async def test_create_closure_empty_objective_fails(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/task-closures", json={"objective": "", "template_id": "bugfix"})
        assert resp.status_code == 400


@pytest.mark.anyio
async def test_create_closure_unknown_template_fails(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "shell"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "未知任务模板"


@pytest.mark.anyio
async def test_get_unknown_closure_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/task-closures/tc_unknown")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_transition_closure(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "增加测试", "template_id": "test"})
        closure_id = create_resp.json()["id"]
        event_resp = await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "planning"})
        assert event_resp.status_code == 200
        assert event_resp.json()["status"] == "planning"


@pytest.mark.anyio
async def test_illegal_transition_returns_error(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "增加测试", "template_id": "test"})
        closure_id = create_resp.json()["id"]
        # pending → completed is illegal, should return 400
        event_resp = await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "completed"})
        assert event_resp.status_code == 400


@pytest.mark.anyio
async def test_record_command_event(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "跑质量门", "template_id": "quality"})
        closure_id = create_resp.json()["id"]
        event_resp = await client.post(f"/task-closures/{closure_id}/events", json={
            "type": "command", "command": "pnpm test", "result": "140 passed",
        })
        assert event_resp.status_code == 200
        data = event_resp.json()
        assert "pnpm test" in data["commands"]
        assert "140 passed" in data["command_results"]


@pytest.mark.anyio
async def test_record_review(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "审查代码", "template_id": "review"})
        closure_id = create_resp.json()["id"]
        review_resp = await client.post(f"/task-closures/{closure_id}/review", json={
            "summary": "全部测试通过", "passed": True,
        })
        assert review_resp.status_code == 200
        data = review_resp.json()
        assert data["review_summary"] == "全部测试通过"
        assert data["next_action"] == "合并到 main"


@pytest.mark.anyio
async def test_unknown_event_type_400(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "test", "template_id": "bugfix"})
        closure_id = create_resp.json()["id"]
        event_resp = await client.post(f"/task-closures/{closure_id}/events", json={"type": "execute_shell"})
        assert event_resp.status_code == 400


@pytest.mark.anyio
async def test_event_on_unknown_closure_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/task-closures/unknown/events", json={"type": "command", "command": "ls", "result": "ok"})
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_api_does_not_trigger_tool_execution(app):
    """API endpoints only record evidence, never execute tools."""
    import inspect
    from bolt_core.task_closure_api import router
    for route in router.routes:
        assert "execute" not in route.name
        assert "approve" not in route.name
        assert "push" not in route.name
        assert "release" not in route.name
