from bolt_core.execution_audit_diagnostics import ExecutionAuditDiagnosticsService
from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_permission_bridge import ExecutionPermissionBridgeService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.execution_result_ingestion import ExecutionResultIngestionService
from bolt_core.permission_queue import PermissionQueue
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_protocol import ToolResult


def test_clean_execution_flow_has_no_diagnostics(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    closure = closures.start("修复拼写", "bugfix")
    item = queue.create_item(closure.id, "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoff = handoffs.create_from_queue_item(item)
    bridge = ExecutionPermissionBridgeService(handoffs, permissions, workspace=str(tmp_path))
    requested = bridge.request_permission(handoff.id, run_id="run_1")
    ExecutionResultIngestionService(handoffs, queue, closures).ingest(ToolResult.executed(requested.permission_request_id or "", "12 passed"))

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics()

    assert diagnostics == []


def test_waiting_permission_without_pending_is_blocking(tmp_path):
    queue, handoffs, _, closures = _services(tmp_path)
    closure, handoff = _waiting_handoff(queue, handoffs, closures)

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, PermissionQueue(), closures).list_diagnostics(closure.id)

    assert diagnostics[0]["code"] == "missing_pending_permission"
    assert diagnostics[0]["severity_label"] == "阻断"


def test_completed_handoff_requires_completed_queue(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    closure, handoff = _approved_handoff(queue, handoffs, closures)
    handoffs.complete(handoff.id, "用户已完成")

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics(closure.id)

    assert diagnostics[0]["code"] == "handoff_completed_queue_not_completed"
    assert diagnostics[0]["severity_label"] == "警告"


def test_failed_handoff_requires_failed_queue(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    closure, handoff = _approved_handoff(queue, handoffs, closures)
    handoffs.fail_with_permission(handoff.id, "rejected", "用户拒绝")

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics(closure.id)

    assert diagnostics[0]["code"] == "handoff_failed_queue_not_failed"


def test_completed_verification_handoff_requires_closure_command(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    closure, handoff = _approved_handoff(queue, handoffs, closures)
    handoffs.complete_with_permission(handoff.id, "executed", "12 passed")
    queue.mark_completed(handoff.queue_item_id, "12 passed")

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics(closure.id)

    assert diagnostics[0]["code"] == "missing_closure_command_evidence"


def test_queue_item_pointing_missing_closure_is_reported(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    queue.create_item("cl_missing", "manual_review", "补充验证证据", "缺少证据", "read_only")

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics()

    assert diagnostics[0]["code"] == "queue_missing_closure"


def test_handoff_pointing_missing_queue_item_is_reported(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    closure = closures.start("修复拼写", "bugfix")
    handoffs._records["eh_orphan"] = handoffs.create_from_queue_item(queue.create_item(closure.id, "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest"))
    handoffs._records["eh_orphan"].queue_item_id = "eq_missing"

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics(closure.id)

    assert any(item["code"] == "handoff_missing_queue_item" for item in diagnostics)


def test_multiple_open_handoffs_for_same_queue_item_is_reported(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    closure, handoff = _approved_handoff(queue, handoffs, closures)
    duplicate = handoffs.create_from_queue_item(queue.get_item(handoff.queue_item_id))
    duplicate.id = "eh_duplicate"
    handoffs._records[duplicate.id] = duplicate

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics(closure.id)

    assert any(item["code"] == "multiple_open_handoffs" for item in diagnostics)


def test_pending_permission_without_handoff_binding_is_reported(tmp_path):
    queue, handoffs, permissions, closures = _services(tmp_path)
    closure = closures.start("修复拼写", "bugfix")
    item = queue.create_item(closure.id, "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoff = handoffs.create_from_queue_item(item)
    bridge = ExecutionPermissionBridgeService(handoffs, permissions, workspace=str(tmp_path))
    requested = bridge.request_permission(handoff.id, run_id="run_1")
    handoffs.get_record(handoff.id).permission_request_id = "tool_missing"

    diagnostics = ExecutionAuditDiagnosticsService(queue, handoffs, permissions, closures).list_diagnostics(closure.id)

    assert any(item["code"] == "permission_unbound_handoff" for item in diagnostics)
    assert requested.permission_status == "pending_permission"


def _services(tmp_path):
    return ExecutionQueueService(), ExecutionHandoffService(), PermissionQueue(), TaskClosureService()


def _approved_handoff(queue, handoffs, closures):
    closure = closures.start("修复拼写", "bugfix")
    item = queue.create_item(closure.id, "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    return closure, handoffs.create_from_queue_item(item)


def _waiting_handoff(queue, handoffs, closures):
    closure, handoff = _approved_handoff(queue, handoffs, closures)
    handoffs.mark_permission_requested(handoff.id, "tool_1", "pending_permission", str(closure.id))
    return closure, handoff
