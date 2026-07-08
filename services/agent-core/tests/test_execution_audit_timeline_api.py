import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.tool_executor import ReadOnlyToolExecutor, ToolExecution


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / "execution-audit.json")


@pytest.mark.anyio
async def test_execution_audit_timeline_api_returns_chinese_events(app, monkeypatch):
    def execute_spy(self, request):
        return ToolExecution(request.id, "executed", "12 passed", None)

    monkeypatch.setattr(ReadOnlyToolExecutor, "execute", execute_spy)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写"})
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run.json()["id"]})
        closure_id = closure.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        proposed = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        item = next(item for item in proposed.json() if item["kind"] == "verification_command")
        await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        requested = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        await client.post(f"/permissions/{requested.json()['permission_request_id']}/approve")

        resp = await client.get(f"/task-closures/{closure_id}/execution-audit-timeline")

    assert resp.status_code == 200
    labels = [event["label"] for event in resp.json()]
    assert "待处理" in labels
    assert "已批准队列" in labels
    assert "已申请权限" in labels
    assert "等待权限" in labels
    assert "已执行" in labels
    assert "已记录闭环证据" in labels
    assert all(event["summary"] for event in resp.json())


@pytest.mark.anyio
async def test_execution_audit_timeline_api_empty_closure_returns_empty(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        closure = await client.post("/task-closures", json={"objective": "更新文档", "template_id": "docs"})
        resp = await client.get(f"/task-closures/{closure.json()['id']}/execution-audit-timeline")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_execution_audit_timeline_api_missing_closure_returns_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/task-closures/missing/execution-audit-timeline")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "任务闭环不存在"


@pytest.mark.anyio
async def test_audit_timeline_source_filter_queue(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写"})
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run.json()["id"]})
        closure_id = closure.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        proposed = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        item = next(item for item in proposed.json() if item["kind"] == "verification_command")
        await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        requested = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        await client.post(f"/permissions/{requested.json()['permission_request_id']}/approve")

        resp = await client.get(f"/audit-timeline?closure_id={closure_id}&source=queue")

    assert resp.status_code == 200
    assert all(e["source"] == "queue" for e in resp.json()["events"])
    assert any(e["status"] == "pending" for e in resp.json()["events"])


@pytest.mark.anyio
async def test_audit_timeline_source_filter_handoff(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写"})
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run.json()["id"]})
        closure_id = closure.json()["id"]
        proposed = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        item = next(item for item in proposed.json() if item["kind"] == "verification_command")
        await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        requested = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        await client.post(f"/permissions/{requested.json()['permission_request_id']}/approve")

        resp = await client.get(f"/audit-timeline?closure_id={closure_id}&source=handoff")

    assert resp.status_code == 200
    assert all(e["source"] == "handoff" for e in resp.json()["events"])
    assert any(e["status"] == "created" for e in resp.json()["events"])
