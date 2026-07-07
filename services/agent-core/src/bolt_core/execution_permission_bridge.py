"""Request-only bridge from handoff records to PermissionGate pending permissions."""
from __future__ import annotations

from collections.abc import Callable
import time

from bolt_core.execution_handoff import ExecutionHandoffRecord, ExecutionHandoffService
from bolt_core.permission_gate import PermissionGate
from bolt_core.permission_queue import PermissionQueue
from bolt_core.tool_protocol import ToolRequest


class ExecutionPermissionBridgeInvalidRequest(ValueError):
    pass


class ExecutionPermissionBridgeService:
    """Creates pending permissions only. Does NOT execute, approve, create goals, or run loops."""

    def __init__(self, handoffs: ExecutionHandoffService, permissions: PermissionQueue,
                 workspace: str | Callable[[ExecutionHandoffRecord], tuple[str, str]]) -> None:
        self._handoffs = handoffs
        self._permissions = permissions
        self._workspace = workspace

    def request_permission(self, handoff_id: str, run_id: str | None = None) -> ExecutionHandoffRecord:
        record = self._handoffs.get_record(handoff_id)
        if record.status in ("completed", "failed"):
            raise ExecutionPermissionBridgeInvalidRequest(f"cannot request permission for handoff in status {record.status}")
        if record.permission_request_id and self._permissions.has_pending(record.permission_request_id):
            return record
        if record.handoff_type != "manual_verification":
            raise ExecutionPermissionBridgeInvalidRequest("只支持人工验证交接申请执行权限")
        if not record.command:
            raise ExecutionPermissionBridgeInvalidRequest("缺少验证命令")

        stale_request_id = record.permission_request_id
        permission_run_id, workspace = self._permission_target(record, run_id)
        request = ToolRequest.create("shell.execute", "command", {"command": record.command, "workdir": workspace})
        decision = PermissionGate(workspace).evaluate(request)
        if decision.status == "denied":
            self._handoffs.mark_bridge_failed(record.id, "denied", decision.reason)
            return self._handoffs.get_record(record.id)

        pending = self._permissions.add(permission_run_id, request, decision)
        record.run_id = permission_run_id
        updated = self._handoffs.mark_permission_requested(record.id, pending.request_id, pending.status, workspace)
        if stale_request_id:
            updated = self._handoffs.mark_bridge_note(record.id, f"旧权限请求已过期，已重新申请：{stale_request_id}")
        else:
            updated.updated_at = time.time()
        return updated

    def _permission_target(self, record: ExecutionHandoffRecord, fallback_run_id: str | None) -> tuple[str, str]:
        if callable(self._workspace):
            return self._workspace(record)
        if record.run_id and record.permission_workspace:
            return record.run_id, record.permission_workspace
        return fallback_run_id or "execution_bridge", self._workspace
