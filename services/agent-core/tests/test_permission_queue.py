from bolt_core.permission_gate import PermissionDecision
from bolt_core.permission_queue import PermissionQueue
from bolt_core.tool_protocol import ToolRequest


def test_add_pending_permission_from_decision():
    queue = PermissionQueue()
    request = ToolRequest.create("shell.run", "command", {"command": "pnpm test"})
    decision = PermissionDecision(request.id, "confirm", "pending_permission", "safe command execution")

    pending = queue.add("run_1", request, decision)

    assert pending.request_id == request.id
    assert pending.status == "pending_permission"
    assert queue.pending()[0].tool == "shell.run"


def test_approve_permission_removes_it_from_pending():
    queue = PermissionQueue()
    request = ToolRequest.create("shell.run", "command", {"command": "pnpm test"})
    decision = PermissionDecision(request.id, "confirm", "pending_permission", "safe command execution")
    queue.add("run_1", request, decision)

    approved = queue.approve(request.id)

    assert approved.status == "approved"
    assert queue.pending() == []


def test_reject_permission_removes_it_from_pending():
    queue = PermissionQueue()
    request = ToolRequest.create("shell.run", "command", {"command": "pnpm test"})
    decision = PermissionDecision(request.id, "confirm", "pending_permission", "safe command execution")
    queue.add("run_1", request, decision)

    rejected = queue.reject(request.id)

    assert rejected.status == "rejected"
    assert queue.pending() == []
