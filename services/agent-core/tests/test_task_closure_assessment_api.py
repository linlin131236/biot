"""Tests for task closure verification plan and assessment API endpoints."""
import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.anyio
async def test_get_verification_plan_returns_checks(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
        closure_id = create_resp.json()["id"]

        resp = await client.get(f"/task-closures/{closure_id}/verification-plan")

        assert resp.status_code == 200
        assert resp.json()["checks"]


@pytest.mark.anyio
async def test_get_assessment_returns_status_summary_missing_and_repair(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
        closure_id = create_resp.json()["id"]

        resp = await client.get(f"/task-closures/{closure_id}/assessment")

        data = resp.json()
        assert data["status"] == "missing_evidence"
        assert data["summary"] == "缺少验证证据"
        assert data["missing"]
        assert data["repair_suggestions"]


@pytest.mark.anyio
async def test_post_assessment_can_complete_passed_closure(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
        closure_id = create_resp.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "command", "command": "pytest", "result": "12 passed"})

        resp = await client.post(f"/task-closures/{closure_id}/assessment")

        assert resp.json()["status"] == "completed"
        assert resp.json()["next_action"] == "已完成"


@pytest.mark.anyio
async def test_post_assessment_keeps_pending_permission_waiting(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
        closure_id = create_resp.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "permission", "id": "perm_44"})
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "planning"})
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "executing"})
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "transition", "target": "waiting_permission"})

        resp = await client.post(f"/task-closures/{closure_id}/assessment")

        assert resp.json()["status"] == "waiting_permission"
        assert resp.json()["next_action"] == "等待人工批准"


@pytest.mark.anyio
async def test_assessment_unknown_closure_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        plan_resp = await client.get("/task-closures/missing/verification-plan")
        get_resp = await client.get("/task-closures/missing/assessment")
        post_resp = await client.post("/task-closures/missing/assessment")

        assert plan_resp.status_code == 404
        assert get_resp.status_code == 404
        assert post_resp.status_code == 404


@pytest.mark.anyio
async def test_assessment_route_names_are_safe(app):
    from bolt_core.task_closure_api import router

    for route in router.routes:
        assert "execute" not in route.name
        assert "approve" not in route.name
        assert "push" not in route.name
        assert "release" not in route.name
