"""Read-only execution audit timeline. Aggregates records only; never executes."""
from __future__ import annotations

from bolt_core.execution_handoff import ExecutionHandoffRecord, ExecutionHandoffService
from bolt_core.execution_queue import ExecutionQueueItem, ExecutionQueueService
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.evidence_redactor import redact


class ExecutionAuditTimelineService:
    """Builds a Chinese audit summary for one closure without mutating state."""

    def __init__(self, queue: ExecutionQueueService, handoffs: ExecutionHandoffService, closures: TaskClosureService) -> None:
        self._queue = queue
        self._handoffs = handoffs
        self._closures = closures

    def for_closure(self, closure_id: str) -> list[dict]:
        events: list[dict] = []
        queue_items = self._queue.list_items(closure_id)
        handoffs = self._handoffs.list_records(closure_id)
        handoffs_by_item = {record.queue_item_id: record for record in handoffs}
        closure = self._closures.load(closure_id)

        for item in queue_items:
            events.append(_event("queue", "pending", "待处理", f"队列项等待人工处理：{redact(item.title)}", item.created_at, closure_id, item.id))
            if item.status in ("approved", "completed", "failed"):
                events.append(_event("queue", "approved", "已批准队列", f"队列项已由人工批准：{redact(item.title)}", item.created_at + 0.001, closure_id, item.id))
            if item.status == "rejected":
                events.append(_event("queue", "rejected", "已拒绝", redact(item.reason) or "队列项已被拒绝", item.created_at + 0.001, closure_id, item.id))
            if item.status == "failed":
                events.append(_event("queue", "failed", "已失败", redact(item.result) or "队列项已失败", item.created_at + 0.002, closure_id, item.id))

        for record in handoffs:
            base_time = _handoff_base_time(record, queue_items)
            events.append(_handoff_event(record, "created", "已创建交接", "已创建安全交接记录", base_time))
            if record.permission_request_id:
                events.append(_handoff_event(record, "permission_requested", "已申请权限", "已创建待人工处理的权限请求", base_time + 0.001))
                events.append(_handoff_event(record, "pending_permission", "等待权限", "权限请求正在等待人工处理", base_time + 0.002))
            if record.permission_status == "executed":
                events.append(_handoff_event(record, "executed", "已执行", "权限执行已返回结果", base_time + 0.003))
            if record.permission_status == "rejected":
                events.append(_handoff_event(record, "rejected", "已拒绝", "权限请求已被拒绝", base_time + 0.003))
            if record.status == "failed" and record.permission_status != "rejected":
                events.append(_handoff_event(record, "failed", "已失败", redact(record.result or record.bridge_error or "执行交接已失败"), base_time + 0.003))

        if closure is not None:
            for command, result in zip(closure.commands, closure.command_results):
                record = _handoff_for_command(handoffs, command)
                item_id = record.queue_item_id if record is not None else None
                handoff_id = record.id if record is not None else None
                permission_id = record.permission_request_id if record is not None else None
                events.append(_event("closure", "evidence_recorded", "已记录闭环证据", f"已记录验证命令：{redact(command)}；结果：{redact(result)}", _evidence_time(record, queue_items), closure_id, item_id, handoff_id, permission_id))

        return sorted(events, key=lambda event: (event["occurred_at"], event["id"]))


def _event(source: str, status: str, label: str, summary: str, occurred_at: float, closure_id: str,
           queue_item_id: str | None = None, handoff_id: str | None = None, permission_request_id: str | None = None) -> dict:
    parts = [source, status, closure_id, queue_item_id or "", handoff_id or "", permission_request_id or "", f"{occurred_at:.6f}"]
    return {
        "id": "audit_" + "_".join(part for part in parts if part),
        "closure_id": closure_id,
        "source": source,
        "status": status,
        "label": label,
        "summary": summary,
        "occurred_at": occurred_at,
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "permission_request_id": permission_request_id,
    }


def _handoff_event(record: ExecutionHandoffRecord, status: str, label: str, summary: str, occurred_at: float) -> dict:
    return _event("handoff", status, label, summary, occurred_at, record.closure_id, record.queue_item_id, record.id, record.permission_request_id)


def _handoff_for_command(handoffs: list[ExecutionHandoffRecord], command: str) -> ExecutionHandoffRecord | None:
    for record in handoffs:
        if record.command == command:
            return record
    return None


def _handoff_base_time(record: ExecutionHandoffRecord, items: list[ExecutionQueueItem]) -> float:
    for item in items:
        if item.id == record.queue_item_id:
            return item.created_at + 0.002
    return record.created_at


def _evidence_time(record: ExecutionHandoffRecord | None, items: list[ExecutionQueueItem]) -> float:
    if record is not None:
        return _handoff_base_time(record, items) + 0.004
    if items:
        return max(item.created_at for item in items) + 0.004
    return 0.0
