from pathlib import Path
from uuid import uuid4

from bolt_core.agent_loop import AgentLoop, AgentLoopResult, AgentStepResult
from bolt_core.conversation import ConversationStore
from bolt_core.conversation_coordinator import ConversationCoordinator
from bolt_core.document_gardener import DocumentGardener
from bolt_core.failure_memory import ToolFailure
from bolt_core.file_writer import apply_file_write, change_set_json, propose_file_write
from bolt_core.harness_file_changes import (
    apply_pending_file_patch, apply_pending_file_write, queue_file_patch,
    queue_file_write,
)
from bolt_core.memory_consolidator import MemoryConsolidationResult, MemoryConsolidator
from bolt_core.memory_store import MemoryRecord, MemoryStore
from bolt_core.model_settings import ModelSettingsStatus, ModelSettingsStore
from bolt_core.patch_engine import ChangeSet, apply_change_set, build_change_set
from bolt_core.goal_service import GoalService
from bolt_core.goal_coordinator import GoalCoordinator
from bolt_core.harness_state import HarnessRun, HarnessState
from bolt_core.permission_gate import PermissionGate
from bolt_core.permission_queue import PendingPermission, PermissionQueue
from bolt_core.perception import PerceptionService
from bolt_core.path_guard import PathGuard
from bolt_core.perception_types import PerceptionSnapshot, dataclass_dict
from bolt_core.terminal_service import TerminalService
from bolt_core.task_closure_recorder import TaskClosureRecorder
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_executor import ReadOnlyToolExecutor, ToolExecution
from bolt_core.tool_protocol import ToolRequest, ToolResult
from bolt_core.trace import TraceEvent, TraceLog
from bolt_core.workspace_lock import resolve_run_workspace
from bolt_core.workspace_credential_gate import LockedWorkspace
from bolt_core.persistence.runtime_harness import (
    assert_run_open, clear_pending_permission, ensure_runtime, finish_runtime,
    finish_step_runtime, persist_pending_permission, register_run, restore_runs,
    update_runtime,
)
class Harness:
    def __init__(self, workspace: str, memory_store: MemoryStore | None = None,
                 memory_db_path: str | None = None,
                 task_closure_service: TaskClosureService | None = None,
                 locked_workspace: str | None = None, model_gateway=None,
                 locked_workspace_binding: LockedWorkspace | None = None, persistence=None,
                 credential_store=None) -> None:
        self.workspace = str(Path(workspace).resolve())
        self.locked_workspace = str(Path(locked_workspace).resolve()) if locked_workspace else None
        self.memory = memory_store or MemoryStore(memory_db_path)
        self.permissions = PermissionQueue()
        self.model_settings = ModelSettingsStore(repository=persistence, credential_store=credential_store)
        self.locked_workspace_binding = locked_workspace_binding
        self.agent_loop = AgentLoop(gateway=model_gateway)
        self.consolidator = MemoryConsolidator()
        self.terminal = TerminalService(self.workspace)
        self.goal_service = GoalService(self.workspace)
        self.task_closure_service = task_closure_service; self.task_closure_recorder = TaskClosureRecorder(task_closure_service)
        self.persistence = persistence
        self._workspace_id = persistence.save_workspace(self.workspace) if persistence is not None else None
        self.conversation_store = None if persistence is not None else ConversationStore(str(Path(self.workspace) / ".bolt" / "conversations.db"))
        self.conversations = ConversationCoordinator(self.workspace, persistence, self.conversation_store)
        self.goals = GoalCoordinator(self.workspace, persistence, self.goal_service)
        self._state = HarnessState(); self.runs = self._state.runs; self.traces = self._state.traces
        self._state_lock = self._state.lock
        restore_runs(self)

    def create_run(self, goal: str, workspace: str | None = None) -> HarnessRun:
        run = HarnessRun(id=f"run_{uuid4().hex[:12]}", goal=goal, workspace=resolve_run_workspace(workspace, self.workspace, self.locked_workspace))
        trace = self._register_run(run)
        self._ensure_repository_runtime(run)
        trace.record("run.created", {"goal": goal, "workspace": run.workspace})
        self._capture_perception(run)
        return run

    def register_internal_run(self, run_id: str, goal: str, workspace: str | None = None) -> HarnessRun:
        if run_id in self._state.runs:
            return self._state.runs[run_id]
        run = HarnessRun(id=run_id, goal=goal, workspace=resolve_run_workspace(workspace, self.workspace, self.locked_workspace))
        trace = self._register_run(run)
        self._ensure_repository_runtime(run)
        trace.record("run.created", {"goal": goal, "workspace": run.workspace})
        return run

    def submit_tool_request(self, run_id: str, request: ToolRequest) -> ToolResult:
        assert_run_open(self, run_id)
        run_immediately = False
        with self._state_lock:
            self._trace_log(run_id).record("tool.requested", {"tool": request.tool})
            decision = PermissionGate(self._workspace(run_id)).evaluate(request)
            self._trace_log(run_id).record("permission.evaluated", {"status": decision.status})
            if decision.status == "denied":
                return self._record_task_closure_tool_result(run_id, self._deny(request, decision.reason))
            if decision.action == "allow":
                self._trace_log(run_id).record("permission.auto_allowed", {"request_id": request.id})
                run_immediately = True
            if request.tool == "file.write":
                return self._record_task_closure_tool_result(run_id, self._queue_file_write(run_id, request, decision))
            if request.tool == "file.patch":
                return self._record_task_closure_tool_result(run_id, self._queue_file_patch(run_id, request, decision))
            if not run_immediately:
                pending = self.permissions.add(run_id, request, decision)
                persist_pending_permission(self, run_id, pending)
                self._trace_log(run_id).record("permission.pending", {"request_id": request.id})
                return self._record_task_closure_tool_result(run_id, ToolResult.pending(request.id, decision.reason))
        execution = self._execute(run_id, request)
        return self._record_task_closure_tool_result(run_id, self._result_from_execution(request, execution))
    def trace(self, run_id: str) -> list[TraceEvent]: return self._trace_log(run_id).events()
    def pending_permissions(self) -> list[PendingPermission]:
        return self.permissions.pending()
    def approve_permission(self, request_id: str) -> ToolResult:
        with self._state_lock:
            item = self.permissions.approve(request_id)
            clear_pending_permission(self, item.run_id, item.request_id)
            self._trace_log(item.run_id).record("permission.approved", {"request_id": request_id})
            if item.tool == "file.write":
                return self._apply_file_write(item)
            if item.tool == "file.patch":
                return self._apply_file_patch(item)
            request = ToolRequest(item.request_id, item.tool, item.operation, item.payload)
            execution = self._execute(item.run_id, request)
            return self._result_from_execution(request, execution)

    def reject_permission(self, request_id: str) -> ToolResult:
        with self._state_lock:
            item = self.permissions.reject(request_id)
            clear_pending_permission(self, item.run_id, item.request_id)
            self._trace_log(item.run_id).record("permission.rejected", {"request_id": request_id})
            if item.tool in ("file.write", "file.patch"):
                self._trace_log(item.run_id).record("change.rejected", {"request_id": request_id})
            return ToolResult.rejected(request_id, "rejected by user")
    def p0_context(self) -> dict[str, list]: return self.memory.p0_context()
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
            return self.memory.search(query, kind=kind, scope=scope, status=status or "active")
        return self.memory.list(kind=kind, scope=scope, status=status)

    def resolve_memory(self, memory_id: str) -> MemoryRecord:
        return self.memory.resolve(memory_id)

    def consolidate_memory(self) -> MemoryConsolidationResult:
        return self.consolidator.consolidate(self.memory)

    def run_document_gardener(self, run_id: str) -> ToolResult:
        proposals = DocumentGardener(self._workspace(run_id), self.memory).proposals()
        if not proposals:
            self._trace_log(run_id).record("maintenance.document_gardener.completed", {"proposals": 0})
            return ToolResult.executed(f"maintenance_{uuid4().hex[:12]}", "no failure patterns to propose")
        proposal = proposals[0]
        request = ToolRequest.create("file.write", "write", {"path": proposal.path, "proposed_content": proposal.content})
        result = self.submit_tool_request(run_id, request)
        self._trace_log(run_id).record("maintenance.document_gardener.proposed", {"path": proposal.path})
        return result

    def run_agent_step(self, run_id: str) -> AgentStepResult:
        assert_run_open(self, run_id)
        run, trace = self._run(run_id), self._trace_log(run_id)
        status = self.model_settings.status()
        if status.state == "blocked":
            trace.record("llm.blocked", {"reason": status.blocked_reason})
            finish_step_runtime(self, run_id, "failed")
            return AgentStepResult("failed", "", None, status.blocked_reason)
        config = self.model_settings.config()
        memories = self._agent_memories()
        result = self.agent_loop.run_step(
            run.goal, config, self.p0_context(), trace,
            lambda req: self.submit_tool_request(run_id, req), memories,
            self.locked_workspace_binding,
        )
        if result.status in ("completed", "failed"):
            finish_step_runtime(self, run_id, result.status)
        return result

    def run_agent_loop(self, run_id: str, max_steps: int = 50) -> AgentLoopResult:
        assert_run_open(self, run_id)
        run, trace = self._run(run_id), self._trace_log(run_id)
        status = self.model_settings.status()
        if status.state == "blocked":
            trace.record("llm.blocked", {"reason": status.blocked_reason})
            if self.persistence is not None and run.id != "run_execution_bridge":
                finish_runtime(self, run_id, "failed")
            step = AgentStepResult("failed", "", None, status.blocked_reason)
            return AgentLoopResult("failed", 0, step, status.blocked_reason)
        config = self.model_settings.config()
        closure_id = self.task_closure_recorder.start_loop(run_id)
        try:
            result = self.agent_loop.run_loop(run.goal, config, self.p0_context, trace, lambda req: self.submit_tool_request(run_id, req), self._agent_memories, max_steps, self.locked_workspace_binding)
            self.task_closure_recorder.record_loop_result(closure_id, result, max_steps)
        except Exception:
            if self.persistence is not None and run.id != "run_execution_bridge": finish_runtime(self, run_id, "failed")
            raise
        if self.persistence is not None and run.id != "run_execution_bridge":
            if result.status == "pending_permission":
                update_runtime(self, run_id, "waiting_approval")
            else:
                finish_runtime(self, run_id, _runtime_status(result.status))
        return result

    def terminal_poll(self, session_id: str) -> dict:
        return self.terminal.poll(session_id)

    def terminal_kill(self, session_id: str) -> dict:
        return self.terminal.kill(session_id)

    def terminal_list(self) -> list[dict]:
        return self.terminal.list_sessions()

    def terminal_output(self, session_id: str) -> dict:
        return self.terminal.full_output(session_id)

    def _record_task_closure_tool_result(self, run_id: str, result: ToolResult) -> ToolResult:
        if self.task_closure_service:
            closure = self.task_closure_service.find_by_run(run_id)
            if closure is not None:
                self.task_closure_recorder.record_tool_result(closure.id, result)
        return result

    def _agent_memories(self) -> list[MemoryRecord]:
        records = [r for r in self.memory.list(status="active") if r.kind != "failure"]
        perception = [r for r in records if "perception" in r.tags]
        others = [r for r in records if "perception" not in r.tags]
        return (perception + others)[:8]

    def _capture_perception(self, run: HarnessRun) -> None:
        snapshot = PerceptionService(run.workspace).snapshot(run.goal, self.p0_context())
        self._record_workspace_profile(snapshot)
        self._record_perception_snapshot(run.id, snapshot)
        self._trace_log(run.id).record("perception.snapshot.created", {"intent": snapshot.intent.category})

    def _record_workspace_profile(self, snapshot: PerceptionSnapshot) -> None:
        profile = dataclass_dict(snapshot.workspace_profile)
        self.memory.record("project", "workspace_profile", "Workspace profile captured", "perception", ["perception", "workspace_profile"], profile)

    def _record_perception_snapshot(self, run_id: str, snapshot: PerceptionSnapshot) -> None:
        metadata = dataclass_dict(snapshot)
        self.memory.record("session", run_id, "Perception snapshot captured", "perception", ["perception", "snapshot"], metadata)

    def _execute(self, run_id: str, request: ToolRequest) -> ToolExecution:
        self._trace_log(run_id).record("tool.execution.started", {"request_id": request.id})
        if request.tool in ("terminal.spawn", "terminal.poll", "terminal.kill"):
            execution = self.terminal.execute_tool(request)
        elif request.tool in ("web.search", "web.extract"):
            execution = ReadOnlyToolExecutor(self._workspace(run_id)).execute(request)
        else:
            execution = ReadOnlyToolExecutor(self._workspace(run_id)).execute(request)
        event_type = "tool.execution.completed" if execution.status == "executed" else "tool.execution.failed"
        self._trace_log(run_id).record(event_type, {"request_id": request.id})
        return execution

    def _queue_file_write(self, run_id: str, request: ToolRequest, decision) -> ToolResult:
        return queue_file_write(self, run_id, request, decision, propose_file_write, change_set_json)

    def _queue_file_patch(self, run_id: str, request: ToolRequest, decision) -> ToolResult:
        return queue_file_patch(self, run_id, request, decision, PathGuard, build_change_set, change_set_json)

    def _apply_file_write(self, item: PendingPermission) -> ToolResult:
        return apply_pending_file_write(self, item, apply_file_write)

    def _apply_file_patch(self, item: PendingPermission) -> ToolResult:
        return apply_pending_file_patch(self, item, ChangeSet, apply_change_set)

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

    def _workspace(self, run_id: str) -> str: return self._run(run_id).workspace
    def _run(self, run_id: str) -> HarnessRun: return self._state.run(run_id)
    def _trace_log(self, run_id: str) -> TraceLog: return self._state.trace(run_id)
    def _register_run(self, run: HarnessRun) -> TraceLog: return register_run(self, run)
    def _ensure_repository_runtime(self, run: HarnessRun) -> None: ensure_runtime(self, run)


def _runtime_status(status: str) -> str:
    return "completed" if status == "completed" else "failed"
