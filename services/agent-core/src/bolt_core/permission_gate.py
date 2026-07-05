from dataclasses import dataclass

from bolt_core.risk import classify_command, classify_path, classify_search
from bolt_core.tool_protocol import ToolRequest


@dataclass(frozen=True)
class PermissionDecision:
    request_id: str
    action: str
    status: str
    reason: str


class PermissionGate:
    def __init__(self, workspace: str) -> None:
        self.workspace = workspace

    def evaluate(self, request: ToolRequest) -> PermissionDecision:
        if request.tool in ("shell.run", "shell.execute"):
            risk = classify_command(str(request.payload.get("command", "")))
        elif request.tool == "files.search":
            risk = classify_search()
        else:
            risk = classify_path(str(request.payload.get("path", "")), self.workspace, request.operation)
        return PermissionDecision(request.id, risk.action, self._status(risk.action), risk.reason)

    def _status(self, action: str) -> str:
        if action == "deny":
            return "denied"
        if action.startswith("confirm"):
            return "pending_permission"
        return "allowed"
