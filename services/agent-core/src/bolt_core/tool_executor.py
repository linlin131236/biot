import json
from dataclasses import dataclass

from bolt_core.file_reader import read_workspace_file
from bolt_core.file_searcher import SearchHit, search_workspace_files
from bolt_core.shell_executor import execute_shell_command
from bolt_core.tool_protocol import ToolRequest


@dataclass(frozen=True)
class ToolExecution:
    request_id: str
    status: str
    output: str | None
    error: str | None


class FakeToolExecutor:
    def execute(self, request: ToolRequest) -> ToolExecution:
        if request.payload.get("fail") is True:
            return ToolExecution(request.id, "failed", None, "fake execution failed")
        return ToolExecution(request.id, "executed", "fake execution completed", None)


class ReadOnlyToolExecutor:
    def __init__(self, workspace: str) -> None:
        self.workspace = workspace

    def execute(self, request: ToolRequest) -> ToolExecution:
        if request.tool == "file.read":
            return self._read(request)
        if request.tool == "files.search":
            return self._search(request)
        if request.tool == "shell.execute":
            return self._shell(request)
        return ToolExecution(request.id, "failed", None, f"unknown tool: {request.tool}")

    def _read(self, request: ToolRequest) -> ToolExecution:
        path = str(request.payload.get("path", ""))
        outcome = read_workspace_file(path, self.workspace)
        if outcome.status != "executed":
            return ToolExecution(request.id, "failed", None, outcome.error)
        payload = json.dumps({"path": outcome.path, "content": outcome.content})
        return ToolExecution(request.id, "executed", payload, None)

    def _search(self, request: ToolRequest) -> ToolExecution:
        query = str(request.payload.get("query", ""))
        mode = str(request.payload.get("mode", "name"))
        outcome = search_workspace_files(self.workspace, query, mode)
        if outcome.status != "executed":
            return ToolExecution(request.id, "failed", None, outcome.error)
        payload = json.dumps({"query": outcome.query, "hits": [_hit_dict(h) for h in outcome.hits]})
        return ToolExecution(request.id, "executed", payload, None)

    def _shell(self, request: ToolRequest) -> ToolExecution:
        outcome = execute_shell_command(request, self.workspace)
        return ToolExecution(request.id, outcome.status, outcome.output, outcome.error)


def _hit_dict(hit: SearchHit) -> dict:
    return {"path": hit.path, "line": hit.line, "snippet": hit.snippet}
