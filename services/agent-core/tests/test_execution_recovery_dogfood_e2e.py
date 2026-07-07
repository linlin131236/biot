import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.harness import Harness
from bolt_core.tool_executor import ReadOnlyToolExecutor, ToolExecution


@pytest.mark.anyio
async def test_execution_recovery_dogfood_e2e(monkeypatch, tmp_path):
    execute_calls: list[str] = []
    harness_calls: list[str] = []

    def execute_spy(self, request):
        execute_calls.append(request.id)
        return ToolExecution(request.id, "executed", "12 passed", None)

    def loop_spy(self, run_id, max_steps=3):
        harness_calls.append("run_agent_loop")
        raise AssertionError("run_agent_loop must not be called")

    def goal_spy(self, payload):
        harness_calls.append("create_goal")
        raise AssertionError("create_goal must not be called")

    monkeypatch.setattr(ReadOnlyToolExecutor, "execute", execute_spy)
    monkeypatch.setattr(Harness, "run_agent_loop", loop_spy)
    audit_path = tmp_path / "execution-audit.json"
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    first_app = create_app(audit_path)
    first_transport = ASGITransport(app=first_app)
    async with AsyncClient(transport=first_transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写", "workspace": str(workspace)})
        run_id = run.json()["id"]
        monkeypatch.setattr(first_app.state if hasattr(first_app, "state") else Harness, "unused", None, raising=False)
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run_id})
        closure_id = closure.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        missing = await client.get(f"/task-closures/{closure_id}/assessment")
        proposed = await client.post(f"/task-closures/{closure_id}/execution-queue/propose")
        item = next(item for item in proposed.json() if item["kind"] == "verification_command")
        approved = await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        requested = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")
        timeline_waiting = await client.get(f"/task-closures/{closure_id}/execution-audit-timeline")
        pending_before_restart = await client.get("/permissions/pending")

    second_app = create_app(audit_path)
    second_transport = ASGITransport(app=second_app)
    async with AsyncClient(transport=second_transport, base_url="http://test") as client:
        diagnostics_stale = await client.get(f"/execution-audit/diagnostics?closure_id={closure_id}")
        recovered = await client.post(f"/execution-handoffs/{requested.json()['id']}/request-permission")
        pending_after_restart = await client.get("/permissions/pending")
        approved_permission = await client.post(f"/permissions/{recovered.json()['permission_request_id']}/approve")
        timeline_completed = await client.get(f"/task-closures/{closure_id}/execution-audit-timeline")
        queue = await client.get(f"/execution-queue?closure_id={closure_id}")
        handoffs = await client.get(f"/execution-handoffs?closure_id={closure_id}")
        closure_after = await client.get(f"/task-closures/{closure_id}")
        diagnostics_clean = await client.get(f"/execution-audit/diagnostics?closure_id={closure_id}")
        completed = await client.post(f"/task-closures/{closure_id}/assessment")

    waiting_labels = [event["label"] for event in timeline_waiting.json()]
    completed_labels = [event["label"] for event in timeline_completed.json()]
    assert missing.json()["status"] == "missing_evidence"
    assert approved.json()["status"] == "approved"
    assert requested.json()["permission_status"] == "pending_permission"
    assert "等待权限" in waiting_labels
    assert pending_before_restart.json()[0]["payload"]["workdir"] == str(workspace)
    assert diagnostics_stale.json()[0]["code"] == "missing_pending_permission"
    assert recovered.json()["permission_request_id"] != requested.json()["permission_request_id"]
    assert pending_after_restart.json()[0]["run_id"] == run_id
    assert pending_after_restart.json()[0]["payload"]["workdir"] == str(workspace)
    assert approved_permission.json()["status"] == "executed"
    assert execute_calls == [recovered.json()["permission_request_id"]]
    assert queue.json()[0]["status"] == "completed"
    assert handoffs.json()[0]["status"] == "completed"
    assert handoff.json()["command"] in closure_after.json()["commands"]
    assert "12 passed" in closure_after.json()["command_results"]
    assert "已执行" in completed_labels
    assert "已记录闭环证据" in completed_labels
    assert diagnostics_clean.json() == []
    assert completed.json()["status"] == "completed"
    assert harness_calls == []
