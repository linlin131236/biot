from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_permission_bridge import ExecutionPermissionBridgeService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.execution_result_ingestion import ExecutionResultIngestionService
from bolt_core.permission_queue import PermissionQueue
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_protocol import ToolResult


def test_executed_permission_completes_handoff_queue_and_records_command(tmp_path):
    queue, handoffs, closures, record = _waiting_handoff(tmp_path)
    result = ToolResult.executed(record.permission_request_id or "", "12 passed")
    ingestion = ExecutionResultIngestionService(handoffs, queue, closures)

    updated = ingestion.ingest(result)
    closure = closures.load(record.closure_id)

    assert updated is not None
    assert updated.status == "completed"
    assert updated.permission_status == "executed"
    assert queue.get_item(record.queue_item_id).status == "completed"
    assert closure is not None
    assert "pytest" in closure.commands
    assert "12 passed" in closure.command_results


def test_failed_permission_fails_handoff_and_queue_without_closure_completion(tmp_path):
    queue, handoffs, closures, record = _waiting_handoff(tmp_path)
    result = ToolResult.failed(record.permission_request_id or "", "pytest failed")
    ingestion = ExecutionResultIngestionService(handoffs, queue, closures)

    updated = ingestion.ingest(result)
    closure = closures.load(record.closure_id)

    assert updated is not None
    assert updated.status == "failed"
    assert updated.permission_status == "failed"
    assert queue.get_item(record.queue_item_id).status == "failed"
    assert closure is not None
    assert closure.status != "completed"


def test_unknown_request_id_is_ignored(tmp_path):
    queue, handoffs, closures, record = _waiting_handoff(tmp_path)
    ingestion = ExecutionResultIngestionService(handoffs, queue, closures)

    updated = ingestion.ingest(ToolResult.executed("missing", "ignored"))

    assert updated is None
    assert handoffs.get_record(record.id).status == "waiting_permission"
    assert queue.get_item(record.queue_item_id).status == "approved"


def test_repeated_ingestion_does_not_rewrite_terminal_handoff(tmp_path):
    queue, handoffs, closures, record = _waiting_handoff(tmp_path)
    ingestion = ExecutionResultIngestionService(handoffs, queue, closures)

    first = ingestion.ingest(ToolResult.executed(record.permission_request_id or "", "first"))
    second = ingestion.ingest(ToolResult.failed(record.permission_request_id or "", "second"))

    assert first is not None
    assert second is not None
    assert second.status == "completed"
    assert second.result == "first"
    assert queue.get_item(record.queue_item_id).result == "first"


def test_rejected_permission_marks_handoff_failed_without_command_evidence(tmp_path):
    queue, handoffs, closures, record = _waiting_handoff(tmp_path)
    ingestion = ExecutionResultIngestionService(handoffs, queue, closures)

    updated = ingestion.ingest(ToolResult.rejected(record.permission_request_id or "", "rejected by user"))
    closure = closures.load(record.closure_id)

    assert updated is not None
    assert updated.status == "failed"
    assert updated.permission_status == "rejected"
    assert queue.get_item(record.queue_item_id).status == "failed"
    assert closure is not None
    assert "pytest" not in closure.commands


def test_ingestion_service_has_no_execution_or_goal_methods(tmp_path):
    queue, handoffs, closures, _ = _waiting_handoff(tmp_path)
    ingestion = ExecutionResultIngestionService(handoffs, queue, closures)

    assert not hasattr(ingestion, "approve_permission")
    assert not hasattr(ingestion, "run_agent_loop")
    assert not hasattr(ingestion, "create_goal")


def _waiting_handoff(tmp_path):
    closures = TaskClosureService()
    closure = closures.start("修复拼写", "bugfix")
    queue = ExecutionQueueService()
    item = queue.create_item(closure.id, "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    record = handoffs.create_from_queue_item(item)
    bridge = ExecutionPermissionBridgeService(handoffs, PermissionQueue(), workspace=str(tmp_path))
    return queue, handoffs, closures, bridge.request_permission(record.id, run_id="run_1")
