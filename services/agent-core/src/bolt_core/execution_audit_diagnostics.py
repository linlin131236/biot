"""Read-only execution audit consistency diagnostics. Never fixes or executes."""
from __future__ import annotations

from collections import defaultdict

from bolt_core.execution_handoff import ExecutionHandoffRecord, ExecutionHandoffService
from bolt_core.execution_queue import ExecutionQueueItem, ExecutionQueueService
from bolt_core.permission_queue import PermissionQueue
from bolt_core.task_closure_service import TaskClosureService


class ExecutionAuditDiagnosticsService:
    def __init__(self, queue: ExecutionQueueService, handoffs: ExecutionHandoffService,
                 permissions: PermissionQueue, closures: TaskClosureService) -> None:
        self._queue = queue
        self._handoffs = handoffs
        self._permissions = permissions
        self._closures = closures

    def list_diagnostics(self, closure_id: str | None = None) -> list[dict]:
        diagnostics: list[dict] = []
        queue_items = self._queue.list_items(closure_id)
        handoffs = self._handoffs.list_records(closure_id)
        queue_by_id = {item.id: item for item in self._queue.list_items()}
        handoff_by_permission = {record.permission_request_id: record for record in self._handoffs.list_records() if record.permission_request_id}

        for item in queue_items:
            if self._closures.load(item.closure_id) is None:
                diagnostics.append(_diagnostic("queue_missing_closure", "blocking", item.closure_id, item.id, None, None, "队列项指向不存在的闭环任务"))

        for record in handoffs:
            item = queue_by_id.get(record.queue_item_id)
            if item is None:
                diagnostics.append(_diagnostic("handoff_missing_queue_item", "blocking", record.closure_id, record.queue_item_id, record.id, record.permission_request_id, "交接记录指向不存在的队列项"))
                continue
            if record.status == "waiting_permission" and record.permission_request_id and not self._permissions.has_pending(record.permission_request_id):
                diagnostics.append(_diagnostic("missing_pending_permission", "blocking", record.closure_id, record.queue_item_id, record.id, record.permission_request_id, "交接等待权限，但权限队列没有 pending 项"))
            if record.status == "completed" and item.status != "completed":
                diagnostics.append(_diagnostic("handoff_completed_queue_not_completed", "warning", record.closure_id, record.queue_item_id, record.id, record.permission_request_id, "交接已完成，但队列项未完成"))
            if record.status == "failed" and item.status != "failed":
                diagnostics.append(_diagnostic("handoff_failed_queue_not_failed", "warning", record.closure_id, record.queue_item_id, record.id, record.permission_request_id, "交接已失败或权限已拒绝，但队列项未失败"))
            if record.kind == "verification_command" and record.status == "completed" and record.command and not _closure_has_command(self._closures, record.closure_id, record.command):
                diagnostics.append(_diagnostic("missing_closure_command_evidence", "warning", record.closure_id, record.queue_item_id, record.id, record.permission_request_id, "验证命令已完成，但闭环证据缺少对应命令"))

        open_by_item: dict[str, list[ExecutionHandoffRecord]] = defaultdict(list)
        for record in handoffs:
            if record.status not in ("completed", "failed"):
                open_by_item[record.queue_item_id].append(record)
        for item_id, records in open_by_item.items():
            if len(records) > 1:
                first = records[0]
                diagnostics.append(_diagnostic("multiple_open_handoffs", "warning", first.closure_id, item_id, first.id, first.permission_request_id, "同一队列项存在多个未终态交接"))

        for pending in self._permissions.pending():
            record = handoff_by_permission.get(pending.request_id)
            if record is None or (closure_id is not None and record.closure_id != closure_id):
                diagnostics.append(_diagnostic("permission_unbound_handoff", "blocking", closure_id or "", None, None, pending.request_id, "权限请求绑定不到交接记录"))

        return diagnostics


def _diagnostic(code: str, severity: str, closure_id: str, queue_item_id: str | None,
                handoff_id: str | None, permission_request_id: str | None, summary: str) -> dict:
    return {
        "id": "diag_" + "_".join(part for part in [code, closure_id, queue_item_id or "", handoff_id or "", permission_request_id or ""] if part),
        "code": code,
        "severity": severity,
        "severity_label": _severity_label(severity),
        "closure_id": closure_id,
        "queue_item_id": queue_item_id,
        "handoff_id": handoff_id,
        "permission_request_id": permission_request_id,
        "summary": summary,
        "suggestion": "建议人工处理",
    }


def _severity_label(severity: str) -> str:
    if severity == "blocking":
        return "阻断"
    if severity == "warning":
        return "警告"
    return "提示"


def _closure_has_command(closures: TaskClosureService, closure_id: str, command: str) -> bool:
    closure = closures.load(closure_id)
    return closure is not None and command in closure.commands
