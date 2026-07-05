from dataclasses import dataclass
from uuid import uuid4

from bolt_core.agent_loop import AgentLoop, AgentStepResult
from bolt_core.document_gardener import DocumentGardener
from bolt_core.failure_memory import ToolFailure
from bolt_core.file_writer import apply_file_write, change_set_json, propose_file_write
from bolt_core.memory_consolidator import MemoryConsolidationResult, MemoryConsolidator
from bolt_core.memory_store import MemoryRecord, MemoryStore
from bolt_core.model_settings import ModelSettingsStatus, ModelSettingsStore
from bolt_core.permission_gate import PermissionGate
from bolt_core.permission_queue import PendingPermission, PermissionQueue
from bolt_core.perception import PerceptionService
from bolt_core.perception_types import PerceptionSnapshot, dataclass_dict
from bolt_core.tool_executor import ReadOnlyToolExecutor, ToolExecution
from bolt_core.tool_protocol import ToolRequest, ToolResult
from bolt_core.trace import TraceEvent, TraceLog


@dataclass(frozen=True)
class HarnessRun:
    id: str
    goal: str


class Harness:
    def __init__(self, workspace: str, memory_store: MemoryStore | None = None, memory_db_path: str | None = None) -> None:
        self.workspace = workspace
        self.memory = memory_store or MemoryStore(memory_db_path)
        self.gate = PermissionGate(workspace)
        self.permissions = PermissionQueue()
        self.executor = ReadOnlyToolExecutor(workspace)
        self.model_settings = ModelSettingsStore()
        self.agent_loop = AgentLoop()
        self.consolidator = MemoryConsolidator()
        self.perception = PerceptionService(workspace)
        self.runs: dict[str, HarnessRun] = {}
        self.traces: dict[str, TraceLog] = {}

    def create_run(self, goal: str) -> HarnessRun:
        run = HarnessRun(id=f"run_{uuid4().hex[:12]}", goal=goal)
        self.runs[run.id] = run
        self.traces[run.id] = TraceLog(run.id)
        self.traces[run.id].record("run.created", {"goal": goal})
        self._capture_perception(run)
        return run

    def submit_tool_request(self, run_id: str, request: ToolRequest) -> ToolResult:
        self.traces[run_id].record("tool.requested", {"tool": request.tool})
        decision = self.gate.evaluate(request)
        self.traces[run_id].record("permission.evaluated", {"status": decision.status})
        if decision.status == "denied":
            return self._deny(request, decision.reason)
        if decision.action == "allow":
            return self._run_immediate(run_id, request)
        if request.tool == "file.write":
            return self._queue_file_write(run_id, request, decision)
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
        request = ToolRequest(item.request_id, item.tool, item.operation, item.payload)
        execution = self._execute(item.run_id, request)
        return self._result_from_execution(request, execution)

    def reject_permission(self, request_id: str) -> ToolResult:
        item = self.permissions.reject(request_id)
        self.traces[item.run_id].record("permission.rejected", {"request_id": request_id})
        if item.tool == "file.write":
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
            str(payload.get("kind", "session")),
            str(payload.get("scope", "default")),
            str(payload.get("content", "")),
            str(payload.get("source", "api")),
            payload.get("tags") or [],
            payload.get("metadata") or {},
        )

    def query_memory(self, kind: str | None = None, scope: str | None = None, status: str | None = None, query: str | None = None) -> list[MemoryRecord]:
        if query:
            return self.memory.search(query, kind=kind)
        return self.memory.list(kind=kind, scope=scope, status=status)

    def resolve_memory(self, memory_id: str) -> MemoryRecord:
        return self.memory.resolve(memory_id)

    def consolidate_memory(self) -> MemoryConsolidationResult:
        return self.consolidator.consolidate(self.memory)

    def run_document_gardener(self, run_id: str) -> ToolResult:
        proposals = DocumentGardener(self.workspace, self.memory).proposals()
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
        return self.agent_loop.run_step(run.goal, config, self.p0_context(), trace, lambda request: self.submit_tool_request(run_id, request), memories)

    def _agent_memories(self) -> list[MemoryRecord]:
        records = [record for record in self.memory.list(status="active") if record.kind != "failure"]
        perception = [record for record in records if "perception" in record.tags]
        others = [record for record in records if "perception" not in record.tags]
        return (perception + others)[:8]

    def _capture_perception(self, run: HarnessRun) -> None:
        snapshot = self.perception.snapshot(run.goal, self.p0_context())
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
        execution = self.executor.execute(request)
        event_type = "tool.execution.completed" if execution.status == "executed" else "tool.execution.failed"
        self.traces[run_id].record(event_type, {"request_id": request.id})
        return execution

    def _queue_file_write(self, run_id: str, request: ToolRequest, decision) -> ToolResult:
        path = str(request.payload.get("path", ""))
        proposed = str(request.payload.get("proposed_content", ""))
        proposal = propose_file_write(path, proposed, self.workspace)
        if proposal.status != "pending_review" or proposal.change is None:
            return self._deny(request, proposal.error or "change proposal failed")
        payload = {**request.payload, "change_set": proposal.change.__dict__}
        self.permissions.add(run_id, request, decision, payload)
        self.traces[run_id].record("change.proposed", {"request_id": request.id})
        self.traces[run_id].record("permission.pending", {"request_id": request.id})
        return ToolResult.pending(request.id, change_set_json(proposal.change))

    def _apply_file_write(self, item: PendingPermission) -> ToolResult:
        allowed, reason = apply_file_write(item.payload["change_set"])
        event = "change.applied" if allowed else "change.failed"
        self.traces[item.run_id].record(event, {"request_id": item.request_id})
        if allowed:
            return ToolResult.executed(item.request_id, reason)
        request = ToolRequest(item.request_id, item.tool, item.operation, item.payload)
        self._record_execution_failure(request, reason)
        return ToolResult.failed(item.request_id, reason)

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
