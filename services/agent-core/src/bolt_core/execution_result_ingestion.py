"""Ingest existing PermissionGate results into handoff and closure evidence."""
from __future__ import annotations

from bolt_core.execution_handoff import ExecutionHandoffRecord, ExecutionHandoffService
from bolt_core.execution_queue import ExecutionQueueService
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_protocol import ToolResult


class ExecutionResultIngestionService:
    """Records completed permission results only. Does NOT execute, approve, create goals, or run loops."""

    def __init__(self, handoffs: ExecutionHandoffService, queue: ExecutionQueueService, closures: TaskClosureService) -> None:
        self._handoffs = handoffs
        self._queue = queue
        self._closures = closures

    def ingest(self, result: ToolResult) -> ExecutionHandoffRecord | None:
        record = self._handoffs.find_by_permission_request(result.request_id)
        if record is None:
            return None
        if record.status in ("completed", "failed"):
            return record
        if result.status == "executed":
            output = result.output or result.reason
            updated = self._handoffs.complete_with_permission(record.id, "executed", output)
            self._queue.mark_completed(record.queue_item_id, output)
            if record.kind == "verification_command" and record.command:
                self._closures.record_command(record.closure_id, record.command, output)
            return updated
        if result.status == "failed":
            error = result.error or result.reason
            updated = self._handoffs.fail_with_permission(record.id, "failed", error)
            self._queue.mark_failed(record.queue_item_id, error)
            return updated
        if result.status in ("denied", "rejected"):
            reason = result.error or result.reason
            updated = self._handoffs.fail_with_permission(record.id, result.status, reason)
            self._queue.mark_failed(record.queue_item_id, reason)
            return updated
        return record
