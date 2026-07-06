import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.tool_executor import ReadOnlyToolExecutor, ToolExecution


@pytest.mark.anyio
async def test_permission_gated_execution_dogfood_e2e(monkeypatch, tmp_path):
    execute_calls: list[str] = []

    def execute_spy(self, request):
        execute_calls.append(request.id)
        return ToolExecution(request.id, "executed", "12 passed", None)

    monkeypatch.setattr(ReadOnlyToolExecutor, "execute", execute_spy)
    app = create_app(tmp_path / "execution-audit.json")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写", "workspace": str(tmp_path)})
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run.json()["id"]})
        closure_id = closure.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        missing = await client.get(f"/task-closures/{closure_id}/assessment")
        proposed = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        item = next(item for item in proposed.json() if item["kind"] == "verification_command")
        approved_item = await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        requested = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        pending = await client.get("/permissions/pending")
        result = await client.post(f"/permissions/{requested.json()['permission_request_id']}/approve")
        handoffs = await client.get(f"/execution-handoffs?closure_id={closure_id}")
        queue = await client.get(f"/execution-queue?closure_id={closure_id}")
        evidence = await client.get(f"/task-closures/{closure_id}")
        completed = await client.post(f"/task-closures/{closure_id}/assessment")
        pending_after = await client.get("/permissions/pending")

    assert missing.json()["status"] == "missing_evidence"
    assert approved_item.json()["status"] == "approved"
    assert requested.json()["status"] == "waiting_permission"
    assert pending.json()[0]["request_id"] == requested.json()["permission_request_id"]
    assert result.json()["status"] == "executed"
    assert execute_calls == [requested.json()["permission_request_id"]]
    assert handoffs.json()[0]["status"] == "completed"
    assert queue.json()[0]["status"] == "completed"
    assert handoff.json()["command"] in evidence.json()["commands"]
    assert "12 passed" in evidence.json()["command_results"]
    assert completed.json()["status"] == "completed"
    assert pending_after.json() == []
