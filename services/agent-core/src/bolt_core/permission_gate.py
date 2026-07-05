from dataclasses import dataclass

from bolt_core.risk import classify_background_command, classify_command, classify_patch, classify_path, classify_search, classify_web
from bolt_core.tool_protocol import ToolRequest

SUPPORTED_OPERATIONS = {
    "file.read": {"read"},
    "files.search": {"search"},
    "file.write": {"write"},
    "file.patch": {"patch"},
    "shell.execute": {"command"},
    "terminal.spawn": {"spawn"},
    "terminal.poll": {"poll"},
    "terminal.kill": {"kill"},
    "web.search": {"search"},
    "web.extract": {"extract"},
}


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
        unsupported = self._unsupported_reason(request)
        if unsupported:
            return PermissionDecision(request.id, "deny", "denied", unsupported)
        risk = self._classify(request)
        return PermissionDecision(request.id, risk.action, self._status(risk.action), risk.reason)

    def _classify(self, request: ToolRequest):
        if request.tool == "shell.execute":
            return classify_command(str(request.payload.get("command", "")))
        if request.tool == "terminal.spawn":
            return classify_background_command(str(request.payload.get("command", "")))
        if request.tool in ("terminal.poll", "terminal.kill"):
            return classify_command("terminal")
        if request.tool == "files.search":
            return classify_search()
        if request.tool in ("web.search", "web.extract"):
            return classify_web()
        if request.tool == "file.patch":
            return classify_patch(str(request.payload.get("path", "")), self.workspace)
        return classify_path(str(request.payload.get("path", "")), self.workspace, request.operation)

    def _unsupported_reason(self, request: ToolRequest) -> str | None:
        operations = SUPPORTED_OPERATIONS.get(request.tool)
        if operations is None:
            return f"unknown tool: {request.tool}"
        if request.operation not in operations:
            return f"unsupported operation: {request.tool}/{request.operation}"
        return None

    def _status(self, action: str) -> str:
        if action == "deny":
            return "denied"
        if action.startswith("confirm"):
            return "pending_permission"
        return "allowed"
