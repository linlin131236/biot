import pytest

from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_permission_bridge import ExecutionPermissionBridgeService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.harness import Harness
from bolt_core.permission_queue import PermissionQueue


class _NoExecuteHarness:
    def submit_tool_request(self, run_id, request):
        raise AssertionError("submit_tool_request must not be called")

    def approve_permission(self, request_id):
        raise AssertionError("approve_permission must not be called")

    def run_agent_loop(self, run_id, max_steps=3):
        raise AssertionError("run_agent_loop must not be called")


def test_manual_verification_handoff_creates_pending_permission(tmp_path):
    queue, handoffs, record = _manual_handoff()
    permissions = PermissionQueue()
    bridge = ExecutionPermissionBridgeService(handoffs, permissions, workspace=str(tmp_path))

    updated = bridge.request_permission(record.id, run_id="run_1")

    pending = permissions.pending()
    assert updated.status == "waiting_permission"
    assert updated.permission_status == "pending_permission"
    assert updated.permission_request_id == pending[0].request_id
    assert pending[0].tool == "shell.execute"
    assert pending[0].payload == {"command": "pytest", "workdir": str(tmp_path)}
    assert queue.get_item(record.queue_item_id).status == "approved"


def test_repeated_request_permission_does_not_duplicate_permission(tmp_path):
    _, handoffs, record = _manual_handoff()
    permissions = PermissionQueue()
    bridge = ExecutionPermissionBridgeService(handoffs, permissions, workspace=str(tmp_path))

    first = bridge.request_permission(record.id, run_id="run_1")
    second = bridge.request_permission(record.id, run_id="run_1")

    assert second.permission_request_id == first.permission_request_id
    assert len(permissions.pending()) == 1


def test_goal_input_handoff_cannot_request_permission(tmp_path):
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "repair_suggestion", "处理修复建议", "修复失败测试", "workspace_write")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    record = handoffs.create_from_queue_item(item)
    bridge = ExecutionPermissionBridgeService(handoffs, PermissionQueue(), workspace=str(tmp_path))

    with pytest.raises(ValueError, match="只支持人工验证交接"):
        bridge.request_permission(record.id, run_id="run_1")


def test_empty_command_cannot_request_permission(tmp_path):
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", "")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    record = handoffs.create_from_queue_item(item)
    bridge = ExecutionPermissionBridgeService(handoffs, PermissionQueue(), workspace=str(tmp_path))

    with pytest.raises(ValueError, match="缺少验证命令"):
        bridge.request_permission(record.id, run_id="run_1")


def test_denied_command_fails_handoff_without_pending_permission(tmp_path):
    _, handoffs, record = _manual_handoff(command="rm -rf /")
    permissions = PermissionQueue()
    bridge = ExecutionPermissionBridgeService(handoffs, permissions, workspace=str(tmp_path))

    updated = bridge.request_permission(record.id, run_id="run_1")

    assert updated.status == "failed"
    assert updated.permission_status == "denied"
    assert "dangerous" in updated.bridge_error.lower() or updated.bridge_error
    assert permissions.pending() == []


def test_bridge_does_not_call_harness_execution_paths(tmp_path, monkeypatch):
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
    _, handoffs, record = _manual_handoff()
    bridge = ExecutionPermissionBridgeService(handoffs, PermissionQueue(), workspace=str(tmp_path))

    bridge.request_permission(record.id, run_id="run_1")

    assert calls == []


def _manual_handoff(command: str = "pytest"):
    queue = ExecutionQueueService()
    item = queue.create_item("cl_1", "verification_command", "记录验证命令", "缺少测试", "verification_command", command)
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    record = handoffs.create_from_queue_item(item)
    return queue, handoffs, record
