import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app


@pytest.mark.anyio
async def test_execution_audit_diagnostics_api_returns_chinese_fields(tmp_path):
    audit_path = tmp_path / "execution-audit.json"
    first_app = create_app(audit_path)
    first_transport = ASGITransport(app=first_app)
    async with AsyncClient(transport=first_transport, base_url="http://test") as client:
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix"})
        closure_id = closure.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        item = (await client.post(f"/task-closures/{closure_id}/execution-queue/propose")).json()[0]
        await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")

    second_app = create_app(audit_path)
    second_transport = ASGITransport(app=second_app)
    async with AsyncClient(transport=second_transport, base_url="http://test") as client:
        resp = await client.get(f"/execution-audit/diagnostics?closure_id={closure_id}")

    assert resp.status_code == 200
    assert resp.json()[0]["severity_label"] == "阻断"
    assert resp.json()[0]["summary"]
    assert resp.json()[0]["suggestion"] == "建议人工处理"


@pytest.mark.anyio
async def test_execution_audit_diagnostics_api_clean_flow_returns_empty(tmp_path, monkeypatch):
    from bolt_core.tool_executor import ReadOnlyToolExecutor, ToolExecution

    def execute_spy(self, request):
        return ToolExecution(request.id, "executed", "12 passed", None)

    monkeypatch.setattr(ReadOnlyToolExecutor, "execute", execute_spy)
    app = create_app(tmp_path / "execution-audit.json")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写", "workspace": str(tmp_path)})
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run.json()["id"]})
        closure_id = closure.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        item = (await client.post(f"/task-closures/{closure_id}/execution-queue/propose")).json()[0]
        await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        requested = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        await client.post(f"/permissions/{requested.json()['permission_request_id']}/approve")

        resp = await client.get(f"/execution-audit/diagnostics?closure_id={closure_id}")

    assert resp.status_code == 200
    assert resp.json() == []
