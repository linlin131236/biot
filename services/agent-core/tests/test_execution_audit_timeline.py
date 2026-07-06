from bolt_core.execution_audit_timeline import ExecutionAuditTimelineService
from bolt_core.execution_handoff import ExecutionHandoffService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.execution_result_ingestion import ExecutionResultIngestionService
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_protocol import ToolResult


def test_timeline_orders_execution_audit_events(tmp_path):
    queue, handoffs, closures, closure_id, request_id = _completed_flow()
    timeline = ExecutionAuditTimelineService(queue, handoffs, closures).for_closure(closure_id)

    labels = [event["label"] for event in timeline]

    assert labels == [
        "待处理",
        "已批准队列",
        "已创建交接",
        "已申请权限",
        "等待权限",
        "已执行",
        "已记录闭环证据",
    ]
    assert timeline == sorted(timeline, key=lambda event: event["occurred_at"])
    assert {event["closure_id"] for event in timeline} == {closure_id}
    assert any(event["permission_request_id"] == request_id for event in timeline)


def test_empty_closure_returns_empty_timeline():
    queue = ExecutionQueueService()
    handoffs = ExecutionHandoffService()
    closures = TaskClosureService()
    closure = closures.start("更新文档", "docs")

    timeline = ExecutionAuditTimelineService(queue, handoffs, closures).for_closure(closure.id)

    assert timeline == []


def test_timeline_isolated_by_closure():
    queue = ExecutionQueueService()
    handoffs = ExecutionHandoffService()
    closures = TaskClosureService()
    first = closures.start("修复拼写", "bugfix")
    second = closures.start("更新文档", "docs")
    queue.create_item(first.id, "manual_review", "补充验证证据", "缺少证据", "read_only")
    queue.create_item(second.id, "manual_review", "补充验证证据", "缺少证据", "read_only")

    timeline = ExecutionAuditTimelineService(queue, handoffs, closures).for_closure(first.id)

    assert timeline
    assert {event["closure_id"] for event in timeline} == {first.id}


def _completed_flow():
    closures = TaskClosureService()
    closure = closures.start("修复拼写", "bugfix")
    closures.record_file_change(closure.id, "src/app.py")
    queue = ExecutionQueueService()
    item = queue.create_item(closure.id, "verification_command", "记录验证命令", "缺少测试", "verification_command", "pytest")
    queue.approve(item.id)
    handoffs = ExecutionHandoffService()
    handoff = handoffs.create_from_queue_item(item)
    handoffs.mark_permission_requested(handoff.id, "tool_1", "pending_permission")
    ingestion = ExecutionResultIngestionService(handoffs, queue, closures)
    ingestion.ingest(ToolResult.executed("tool_1", "12 passed"))
    return queue, handoffs, closures, closure.id, "tool_1"
