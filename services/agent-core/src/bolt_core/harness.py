import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from bolt_core.agent_loop import AgentLoop, AgentLoopResult, AgentStepResult
from bolt_core.conversation import ConversationStore
from bolt_core.document_gardener import DocumentGardener
from bolt_core.failure_memory import ToolFailure
from bolt_core.file_writer import apply_file_write, change_set_json, propose_file_write
from bolt_core.memory_consolidator import MemoryConsolidationResult, MemoryConsolidator
from bolt_core.memory_store import MemoryRecord, MemoryStore
from bolt_core.model_settings import ModelSettingsStatus, ModelSettingsStore
from bolt_core.patch_engine import build_change_set, apply_change_set
from bolt_core.evidence import EvidenceLog
from bolt_core.goal_service import GoalService
from bolt_core.permission_gate import PermissionGate
from bolt_core.permission_queue import PendingPermission, PermissionQueue
from bolt_core.perception import PerceptionService
from bolt_core.perception_types import PerceptionSnapshot, dataclass_dict
from bolt_core.terminal_service import TerminalService
from bolt_core.tool_executor import ReadOnlyToolExecutor, ToolExecution
from bolt_core.tool_protocol import ToolRequest, ToolResult
from bolt_core.trace import TraceEvent, TraceLog


@dataclass(frozen=True)
class HarnessRun:
    id: str
    goal: str
    workspace: str


class Harness:
    def __init__(self, workspace: str, memory_store: MemoryStore | None = None,
                 memory_db_path: str | None = None) -> None:
        self.workspace = workspace
        self.memory = memory_store or MemoryStore(memory_db_path)
        self.permissions = PermissionQueue()
        self.model_settings = ModelSettingsStore()
        self.agent_loop = AgentLoop()
        self.consolidator = MemoryConsolidator()
        self.terminal = TerminalService(workspace)
        self.goal_service = GoalService(workspace)
        self.conversation_store = ConversationStore(
            str(Path(workspace) / ".bolt" / "conversations.db"))
        self.runs: dict[str, HarnessRun] = {}
        self.traces: dict[str, TraceLog] = {}

    def create_run(self, goal: str, workspace: str | None = None) -> HarnessRun:
        run = HarnessRun(id=f"run_{uuid4().hex[:12]}", goal=goal, workspace=workspace or self.workspace)
        self.runs[run.id] = run
        self.traces[run.id] = TraceLog(run.id)
        self.traces[run.id].record("run.created", {"goal": goal, "workspace": run.workspace})
        self._capture_perception(run)
        return run

    def submit_tool_request(self, run_id: str, request: ToolRequest) -> ToolResult:
        self.traces[run_id].record("tool.requested", {"tool": request.tool})
        decision = PermissionGate(self._workspace(run_id)).evaluate(request)
        self.traces[run_id].record("permission.evaluated", {"status": decision.status})
        if decision.status == "denied":
            return self._deny(request, decision.reason)
        if decision.action == "allow":
            return self._run_immediate(run_id, request)
        if request.tool == "file.write":
            return self._queue_file_write(run_id, request, decision)
        if request.tool == "file.patch":
            return self._queue_file_patch(run_id, request, decision)
        self.permissions.add(run_id, request, decision)
        self.traces[run_id].record("permission.pending", {"request_id": request.id})
        return ToolResult.pending(request.id, decision.reason)

    def trace(self, run_id: str) -> list[TraceEvent]:
        return self.traces[run_id].events()

    def pending_permissions(self) -> list[PendingPermission]:
        return self.permissions.pending()

    def approve_permission(self, request_id: str) -> ToolResult:
        item = self.permissions.approve(request_id)
        self.traces[item.run_id].record("permission.approved", {"request_id": request_id})
        if item.tool == "file.write":
            return self._apply_file_write(item)
        if item.tool == "file.patch":
            return self._apply_file_patch(item)
        request = ToolRequest(item.request_id, item.tool, item.operation, item.payload)
        execution = self._execute(item.run_id, request)
        return self._result_from_execution(request, execution)

    def reject_permission(self, request_id: str) -> ToolResult:
        item = self.permissions.reject(request_id)
        self.traces[item.run_id].record("permission.rejected", {"request_id": request_id})
        if item.tool in ("file.write", "file.patch"):
            self.traces[item.run_id].record("change.rejected", {"request_id": request_id})
        return ToolResult.rejected(request_id, "rejected by user")

    def p0_context(self) -> dict[str, list]:
        return self.memory.p0_context()

    def memory_snapshot(self) -> dict:
        return self.memory.snapshot()

    def model_settings_status(self) -> ModelSettingsStatus:
        return self.model_settings.status()

    def update_model_settings(self, payload: dict) -> ModelSettingsStatus:
        return self.model_settings.update(payload)

    def record_memory(self, payload: dict) -> MemoryRecord:
        return self.memory.record(
            str(payload.get("kind", "session")), str(payload.get("scope", "default")),
            str(payload.get("content", "")), str(payload.get("source", "api")),
            payload.get("tags") or [], payload.get("metadata") or {})

    def query_memory(self, kind=None, scope=None, status=None, query=None) -> list[MemoryRecord]:
        if query:
            return self.memory.search(query, kind=kind)
        return self.memory.list(kind=kind, scope=scope, status=status)

    def resolve_memory(self, memory_id: str) -> MemoryRecord:
        return self.memory.resolve(memory_id)

    def consolidate_memory(self) -> MemoryConsolidationResult:
        return self.consolidator.consolidate(self.memory)

    def run_document_gardener(self, run_id: str) -> ToolResult:
        proposals = DocumentGardener(self._workspace(run_id), self.memory).proposals()
        if not proposals:
            self.traces[run_id].record("maintenance.document_gardener.completed", {"proposals": 0})
            return ToolResult.executed(f"maintenance_{uuid4().hex[:12]}", "no failure patterns to propose")
        proposal = proposals[0]
        request = ToolRequest.create("file.write", "write", {"path": proposal.path, "proposed_content": proposal.content})
        result = self.submit_tool_request(run_id, request)
        self.traces[run_id].record("maintenance.document_gardener.proposed", {"path": proposal.path})
        return result

    def run_agent_step(self, run_id: str) -> AgentStepResult:
        run = self.runs[run_id]
        trace = self.traces[run_id]
        config = self.model_settings.config()
        memories = self._agent_memories()
        return self.agent_loop.run_step(run.goal, config, self.p0_context(), trace, lambda req: self.submit_tool_request(run_id, req), memories)

    def run_agent_loop(self, run_id: str, max_steps: int = 3) -> AgentLoopResult:
        run = self.runs[run_id]
        trace = self.traces[run_id]
        config = self.model_settings.config()
        return self.agent_loop.run_loop(run.goal, config, self.p0_context, trace, lambda req: self.submit_tool_request(run_id, req), self._agent_memories, max_steps)

    # Terminal delegation
    def terminal_poll(self, session_id: str) -> dict:
        return self.terminal.poll(session_id)

    def terminal_kill(self, session_id: str) -> dict:
        return self.terminal.kill(session_id)

    def terminal_list(self) -> list[dict]:
        return self.terminal.list_sessions()

    def terminal_output(self, session_id: str) -> dict:
        return self.terminal.full_output(session_id)

    def _agent_memories(self) -> list[MemoryRecord]:
        records = [r for r in self.memory.list(status="active") if r.kind != "failure"]
        perception = [r for r in records if "perception" in r.tags]
        others = [r for r in records if "perception" not in r.tags]
        return (perception + others)[:8]

    def _capture_perception(self, run: HarnessRun) -> None:
        snapshot = PerceptionService(run.workspace).snapshot(run.goal, self.p0_context())
        self._record_workspace_profile(snapshot)
        self._record_perception_snapshot(run.id, snapshot)
        self.traces[run.id].record("perception.snapshot.created", {"intent": snapshot.intent.category})

    def _record_workspace_profile(self, snapshot: PerceptionSnapshot) -> None:
        profile = dataclass_dict(snapshot.workspace_profile)
        self.memory.record("project", "workspace_profile", "Workspace profile captured", "perception", ["perception", "workspace_profile"], profile)

    def _record_perception_snapshot(self, run_id: str, snapshot: PerceptionSnapshot) -> None:
        metadata = dataclass_dict(snapshot)
        self.memory.record("session", run_id, "Perception snapshot captured", "perception", ["perception", "snapshot"], metadata)

    def _execute(self, run_id: str, request: ToolRequest) -> ToolExecution:
        self.traces[run_id].record("tool.execution.started", {"request_id": request.id})
        if request.tool in ("terminal.spawn", "terminal.poll", "terminal.kill"):
            execution = self.terminal.execute_tool(request)
        elif request.tool in ("web.search", "web.extract"):
            execution = ReadOnlyToolExecutor(self._workspace(run_id)).execute(request)
        else:
            execution = ReadOnlyToolExecutor(self._workspace(run_id)).execute(request)
        event_type = "tool.execution.completed" if execution.status == "executed" else "tool.execution.failed"
        self.traces[run_id].record(event_type, {"request_id": request.id})
        return execution

    def _queue_file_write(self, run_id: str, request: ToolRequest, decision) -> ToolResult:
        path = str(request.payload.get("path", ""))
        proposed = str(request.payload.get("proposed_content", ""))
        proposal = propose_file_write(path, proposed, self._workspace(run_id))
        if proposal.status != "pending_review" or proposal.change is None:
            return self._deny(request, proposal.error or "change proposal failed")
        payload = {**request.payload, "change_set": proposal.change.__dict__}
        self.permissions.add(run_id, request, decision, payload)
        self.traces[run_id].record("change.proposed", {"request_id": request.id})
        self.traces[run_id].record("permission.pending", {"request_id": request.id})
        return ToolResult.pending(request.id, change_set_json(proposal.change))

    def _queue_file_patch(self, run_id: str, request: ToolRequest, decision) -> ToolResult:
        path = str(request.payload.get("path", ""))
        old_string = str(request.payload.get("old_string", ""))
        new_string = str(request.payload.get("new_string", ""))
        from pathlib import Path
        target = Path(path)
        if not target.exists():
            return self._deny(request, f"file not found: {path}")
        try:
            original = target.read_text(encoding="utf-8")
        except OSError as exc:
            return self._deny(request, f"read error: {exc}")
        count = original.count(old_string)
        if count == 0:
            return self._deny(request, "old_string not found in file")
        if count > 1:
            return self._deny(request, f"old_string appears {count} times, must be unique")
        patched = original.replace(old_string, new_string, 1)
        change = build_change_set(path, original, patched)
        payload = {**request.payload, "change_set": change.__dict__}
        self.permissions.add(run_id, request, decision, payload)
        self.traces[run_id].record("change.proposed", {"request_id": request.id})
        self.traces[run_id].record("permission.pending", {"request_id": request.id})
        return ToolResult.pending(request.id, change_set_json(change))

    def _apply_file_write(self, item: PendingPermission) -> ToolResult:
        allowed, reason = apply_file_write(item.payload["change_set"])
        event = "change.applied" if allowed else "change.failed"
        self.traces[item.run_id].record(event, {"request_id": item.request_id})
        if allowed:
            return ToolResult.executed(item.request_id, reason)
        request = ToolRequest(item.request_id, item.tool, item.operation, item.payload)
        self._record_execution_failure(request, reason)
        return ToolResult.failed(item.request_id, reason)

    def _apply_file_patch(self, item: PendingPermission) -> ToolResult:
        change_set = item.payload.get("change_set", {})
        from bolt_core.patch_engine import ChangeSet
        change = ChangeSet(**change_set)
        decision = apply_change_set(change)
        event = "change.applied" if decision.allowed else "change.failed"
        self.traces[item.run_id].record(event, {"request_id": item.request_id})
        if decision.allowed:
            return ToolResult.executed(item.request_id, decision.reason)
        return ToolResult.failed(item.request_id, decision.reason)

    def _run_immediate(self, run_id: str, request: ToolRequest) -> ToolResult:
        self.traces[run_id].record("permission.auto_allowed", {"request_id": request.id})
        execution = self._execute(run_id, request)
        return self._result_from_execution(request, execution)

    def _result_from_execution(self, request: ToolRequest, execution: ToolExecution) -> ToolResult:
        if execution.status == "executed":
            return ToolResult.executed(request.id, execution.output or "")
        self._record_execution_failure(request, execution.error or "execution failed")
        return ToolResult.failed(request.id, execution.error or "execution failed")

    def _record_execution_failure(self, request: ToolRequest, error: str) -> None:
        failure = ToolFailure(request.tool, request.operation, "execution_failed", error, error, "not_fixed")
        self.memory.record_failure(failure, source=request.id)

    def _deny(self, request: ToolRequest, reason: str) -> ToolResult:
        failure = ToolFailure(request.tool, request.operation, "permission_denied", reason, reason, "not_fixed")
        self.memory.record_failure(failure, source=request.id)
        return ToolResult.denied(request.id, reason)

    def _workspace(self, run_id: str) -> str:
        return self.runs[run_id].workspace
