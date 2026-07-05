from dataclasses import dataclass

from bolt_core.permission_gate import PermissionDecision
from bolt_core.tool_protocol import ToolRequest


@dataclass(frozen=True)
class PendingPermission:
    id: str
    run_id: str
    request_id: str
    tool: str
    operation: str
    payload: dict
    action: str
    reason: str
    status: str


class PermissionQueue:
    def __init__(self) -> None:
        self._items: dict[str, PendingPermission] = {}

    def add(self, run_id: str, request: ToolRequest, decision: PermissionDecision, payload: dict | None = None) -> PendingPermission:
        item = PendingPermission(
            id=f"perm_{request.id}",
            run_id=run_id,
            request_id=request.id,
            tool=request.tool,
            operation=request.operation,
            payload=payload or request.payload,
            action=decision.action,
            reason=decision.reason,
            status="pending_permission",
        )
        self._items[request.id] = item
        return item

    def pending(self) -> list[PendingPermission]:
        return [item for item in self._items.values() if item.status == "pending_permission"]

    def approve(self, request_id: str) -> PendingPermission:
        return self._set_status(request_id, "approved")

    def reject(self, request_id: str) -> PendingPermission:
        return self._set_status(request_id, "rejected")

    def _set_status(self, request_id: str, status: str) -> PendingPermission:
        item = self._items[request_id]
        updated = PendingPermission(**{**item.__dict__, "status": status})
        self._items[request_id] = updated
        return updated
