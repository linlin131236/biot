import pytest
from httpx import ASGITransport, AsyncClient

from bolt_core.app import create_app
from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_permission_bridge import ExecutionPermissionBridgeService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.harness import Harness
from bolt_core.permission_queue import PermissionQueue


def test_repeated_request_permission_keeps_existing_pending(tmp_path):
    _, handoffs, record = _manual_handoff(tmp_path)
    permissions = PermissionQueue()
    bridge = ExecutionPermissionBridgeService(handoffs, permissions, workspace=str(tmp_path))

    first = bridge.request_permission(record.id, run_id="run_1")
    second = bridge.request_permission(record.id, run_id="run_1")

    assert second.permission_request_id == first.permission_request_id
    assert len(permissions.pending()) == 1
    assert permissions.has_pending(first.permission_request_id or "")


def test_stale_permission_request_is_recreated_after_restart(tmp_path):
    audit_path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(audit_path)
    first_queue, first_handoffs, record = _manual_handoff(tmp_path, store)
    first_permissions = PermissionQueue()
    first_bridge = ExecutionPermissionBridgeService(first_handoffs, first_permissions, workspace=str(tmp_path))
    first = first_bridge.request_permission(record.id, run_id="run_1")

    restored_handoffs = ExecutionHandoffService(store)
    restored_permissions = PermissionQueue()
    restored_bridge = ExecutionPermissionBridgeService(restored_handoffs, restored_permissions, workspace=str(tmp_path))
    recovered = restored_bridge.request_permission(first.id, run_id="run_1")

    assert recovered.permission_request_id != first.permission_request_id
    assert recovered.permission_status == "pending_permission"
    assert "旧权限请求已过期，已重新申请" in recovered.bridge_error
    assert len(restored_permissions.pending()) == 1
    assert restored_permissions.pending()[0].request_id == recovered.permission_request_id
    assert first_queue.get_item(record.queue_item_id).status == "approved"


@pytest.mark.anyio
async def test_recovered_permission_uses_bound_run_workspace(tmp_path):
    workspace = tmp_path / "user-workspace"
    workspace.mkdir()
    audit_path = tmp_path / "execution-audit.json"
    first_app = create_app(audit_path)
    first_transport = ASGITransport(app=first_app)
    async with AsyncClient(transport=first_transport, base_url="http://test") as client:
        run = await client.post("/harness/runs", json={"goal": "修复拼写", "workspace": str(workspace)})
        closure = await client.post("/task-closures", json={"objective": "修复拼写", "template_id": "bugfix", "run_id": run.json()["id"]})
        closure_id = closure.json()["id"]
        await client.post(f"/task-closures/{closure_id}/events", json={"type": "file_change", "path": "src/app.py"})
        item = (await client.post(f"/task-closures/{closure_id}/execution-queue/propose")).json()[0]
        await client.post(f"/execution-queue/{item['id']}/approve")
        handoff = await client.post(f"/execution-queue/{item['id']}/handoff")
        first = await client.post(f"/execution-handoffs/{handoff.json()['id']}/request-permission")

    second_app = create_app(audit_path)
    second_transport = ASGITransport(app=second_app)
    async with AsyncClient(transport=second_transport, base_url="http://test") as client:
        recovered = await client.post(f"/execution-handoffs/{first.json()['id']}/request-permission")
        pending = await client.get("/permissions/pending")

    assert recovered.json()["permission_request_id"] != first.json()["permission_request_id"]
    assert pending.json()[0]["run_id"] == run.json()["id"]
    assert pending.json()[0]["payload"]["workdir"] == str(workspace)


def test_terminal_handoff_cannot_recreate_permission(tmp_path):
    _, handoffs, record = _manual_handoff(tmp_path)
    handoffs.complete(record.id, "用户已完成")
    bridge = ExecutionPermissionBridgeService(handoffs, PermissionQueue(), workspace=str(tmp_path))

    with pytest.raises(ValueError, match="cannot request permission"):
        bridge.request_permission(record.id, run_id="run_1")


def test_recovery_does_not_call_execution_paths(tmp_path, monkeypatch):
    calls: list[str] = []

    def submit_spy(self, run_id, request):
        calls.append("submit_tool_request")
        raise AssertionError("submit_tool_request must not be called")

    def approve_spy(self, request_id):
        calls.append("approve_permission")
        raise AssertionError("approve_permission must not be called")

    def loop_spy(self, run_id, max_steps=3):
        calls.append("run_agent_loop")
        raise AssertionError("run_agent_loop must not be called")

    monkeypatch.setattr(Harness, "submit_tool_request", submit_spy)
    monkeypatch.setattr(Harness, "approve_permission", approve_spy)
    monkeypatch.setattr(Harness, "run_agent_loop", loop_spy)
    audit_path = tmp_path / "execution-audit.json"
    store = ExecutionAuditStore(audit_path)
    _, first_handoffs, record = _manual_handoff(tmp_path, store)
    first_bridge = ExecutionPermissionBridgeService(first_handoffs, PermissionQueue(), workspace=str(tmp_path))
    first_bridge.request_permission(record.id, run_id="run_1")

    restored = ExecutionHandoffService(store)
    bridge = ExecutionPermissionBridgeService(restored, PermissionQueue(), workspace=str(tmp_path))
    bridge.request_permission(record.id, run_id="run_1")

    assert calls == []


def _manual_handoff(tmp_path, store=None):
    queue = ExecutionQueueService(store)
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService(store)
    record = handoffs.create_from_queue_item(item)
    return queue, handoffs, record
