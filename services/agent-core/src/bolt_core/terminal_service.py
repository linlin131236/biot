"""Terminal process service: spawn, poll, kill, list, output."""

import json as _json

from bolt_core.background_executor import BackgroundExecutor
from bolt_core.tool_protocol import ToolRequest
from bolt_core.tool_executor import ToolExecution


class TerminalService:
    def __init__(self, workspace: str) -> None:
        self.executor = BackgroundExecutor(workspace)
        self.workspace = workspace

    def poll(self, session_id: str) -> dict:
        result = self.executor.poll(session_id)
        return {"session_id": result.session_id, "status": result.status, "output": result.output}

    def kill(self, session_id: str) -> dict:
        result = self.executor.kill(session_id)
        return {"session_id": result.session_id, "status": result.status}

    def list_sessions(self) -> list[dict]:
        return [{"session_id": p.session_id, "status": p.status, "command": p.command}
                for p in self.executor.list_sessions()]

    def full_output(self, session_id: str) -> dict:
        result = self.executor.full_output(session_id)
        return {"session_id": result.session_id, "status": result.status, "output": result.output}

    def execute_tool(self, request: ToolRequest) -> ToolExecution:
        if request.tool == "terminal.spawn":
            command = str(request.payload.get("command", ""))
            workdir = str(request.payload.get("workdir", self.workspace))
            result = self.executor.spawn(command, workdir)
            if result.status == "failed":
                return ToolExecution(request.id, "failed", None, result.output)
            return ToolExecution(request.id, "executed",
                                 _json.dumps({"session_id": result.session_id, "status": result.status}), None)
        if request.tool == "terminal.poll":
            session_id = str(request.payload.get("session_id", ""))
            result = self.executor.poll(session_id)
            return ToolExecution(request.id, "executed",
                                 _json.dumps({"session_id": result.session_id, "status": result.status, "output": result.output}), None)
        if request.tool == "terminal.kill":
            session_id = str(request.payload.get("session_id", ""))
            result = self.executor.kill(session_id)
            return ToolExecution(request.id, "executed",
                                 _json.dumps({"session_id": result.session_id, "status": result.status}), None)
        return ToolExecution(request.id, "failed", None, f"unknown terminal operation: {request.tool}")
