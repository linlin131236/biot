"""TaskClosureService: conservative evidence recorder, no tool execution."""
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from bolt_core.task_closure import (
    TaskClosure, TaskClosureStatus, TaskTemplateId, MAX_RETRIES, can_transition,
)
from bolt_core.task_verification import (
    assess_completion as _assess_completion,
    build_verification_plan,
    verification_assessment_dict,
    verification_plan_dict,
)

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.evidence_redactor import redact


@dataclass
class TaskClosureRecord:
    closure: TaskClosure
    events: list[dict] = field(default_factory=list)


class TaskClosureService:
    """Records task closure evidence. Does NOT execute tools, push, release, or approve permissions."""

    def __init__(self, store: ExecutionAuditStore | None = None) -> None:
        self._store: dict[str, TaskClosureRecord] = {}
        self._audit_store = store
        if store is not None:
            self._restore(store.load().closure_records)

    def start(self, objective: str, template_id: TaskTemplateId,
              run_id: Optional[str] = None, goal_id: Optional[str] = None) -> TaskClosure:
        """Create a new task closure record."""
        closure = TaskClosure(
            id=f"cl_{uuid.uuid4().hex[:12]}",
            objective=objective,
            template_id=template_id,
            run_id=run_id,
            goal_id=goal_id,
            created_at=time.time(),
        )
        self._store[closure.id] = TaskClosureRecord(closure=closure)
        self._save_closures()
        return closure

    def bind_run(self, closure_id: str, run_id: str) -> TaskClosure:
        record = self._record(closure_id)
        record.closure.run_id = run_id
        record.events.append({"type": "bind_run", "run_id": run_id, "ts": time.time()})
        self._save_closures()
        return record.closure

    def bind_goal(self, closure_id: str, goal_id: str) -> TaskClosure:
        record = self._record(closure_id)
        record.closure.goal_id = goal_id
        record.events.append({"type": "bind_goal", "goal_id": goal_id, "ts": time.time()})
        self._save_closures()
        return record.closure

    def find_by_run(self, run_id: str) -> TaskClosure | None:
        for record in self._store.values():
            if record.closure.run_id == run_id:
                return record.closure
        return None

    def find_by_goal(self, goal_id: str) -> TaskClosure | None:
        for record in self._store.values():
            if record.closure.goal_id == goal_id:
                return record.closure
        return None

    def transition(self, closure_id: str, target: TaskClosureStatus) -> TaskClosure:
        """Transition closure to a new status if legal."""
        record = self._record(closure_id)
        closure = record.closure
        if not can_transition(closure.status, target):
            raise ValueError(f"illegal transition: {closure.status} → {target}")
        previous = closure.status
        closure.status = target
        record.events.append({"type": "transition", "from": previous, "to": target, "ts": time.time()})
        self._save_closures()
        return closure

    def record_loop_status(self, closure_id: str, loop_status: str, reason: str = "") -> TaskClosure:
        target = self._loop_target(loop_status, reason)
        closure = self._set_status(closure_id, target, "loop_status", {"loop_status": loop_status, "reason": reason})
        if reason:
            closure.command_results.append(reason)
            self._save_closures()
        return closure

    def record_tool_result(self, closure_id: str, tool_result: dict) -> TaskClosure:
        record = self._record(closure_id)
        request_id = str(tool_result.get("request_id", ""))
        status = str(tool_result.get("status", ""))
        output = str(tool_result.get("output") or tool_result.get("reason") or tool_result.get("error") or "")
        if request_id and status == "pending_permission":
            self.mark_waiting_permission(closure_id, request_id)
        if request_id:
            record.closure.commands.append(f"tool:{request_id}")
        if output:
            record.closure.command_results.append(output)
        if status == "failed":
            self.mark_failed(closure_id, output or "工具执行失败")
        record.events.append({"type": "tool_result", "request_id": request_id, "status": status, "ts": time.time()})
        self._save_closures()
        return record.closure

    def mark_waiting_permission(self, closure_id: str, permission_id: str) -> TaskClosure:
        record = self._record(closure_id)
        if permission_id not in record.closure.permission_request_ids:
            record.closure.permission_request_ids.append(permission_id)
        return self._set_status(closure_id, TaskClosureStatus.WAITING_PERMISSION, "permission", {"id": permission_id})

    def mark_failed(self, closure_id: str, reason: str) -> TaskClosure:
        record = self._record(closure_id)
        if reason:
            record.closure.command_results.append(reason)
        return self._set_status(closure_id, TaskClosureStatus.FAILED, "failed", {"reason": reason})

    def mark_completed(self, closure_id: str, summary: str) -> TaskClosure:
        record = self._record(closure_id)
        record.closure.review_summary = summary
        record.closure.next_action = "已完成"
        return self._set_status(closure_id, TaskClosureStatus.COMPLETED, "completed", {"summary": summary})

    def record_command(self, closure_id: str, command: str, result: str) -> None:
        """Record a verification command and its result."""
        record = self._record(closure_id)
        record.closure.commands.append(redact(command))
        record.closure.command_results.append(redact(result))
        record.events.append({"type": "command", "command": redact(command), "result": redact(result), "ts": time.time()})
        self._save_closures()

    def record_file_change(self, closure_id: str, file_path: str) -> None:
        """Record a changed file."""
        record = self._record(closure_id)
        record.closure.changed_files.append(file_path)
        record.events.append({"type": "file_change", "path": file_path, "ts": time.time()})
        self._save_closures()

    def record_permission(self, closure_id: str, permission_id: str) -> None:
        """Record a permission request ID."""
        record = self._record(closure_id)
        record.closure.permission_request_ids.append(permission_id)
        record.events.append({"type": "permission", "id": permission_id, "ts": time.time()})
        self._save_closures()

    def record_review(self, closure_id: str, summary: str, passed: bool) -> TaskClosure:
        """Record a review summary."""
        record = self._record(closure_id)
        record.closure.review_summary = summary
        record.closure.next_action = "合并到 main" if passed else "需要人工处理"
        record.events.append({"type": "review", "summary": summary, "passed": passed, "ts": time.time()})
        self._save_closures()
        return record.closure

    def should_stop_repairing(self, closure_id: str) -> bool:
        """Check if repair retries have exceeded MAX_RETRIES."""
        return self._record(closure_id).closure.retry_count >= MAX_RETRIES

    def increment_retry(self, closure_id: str) -> None:
        """Increment retry count."""
        self._record(closure_id).closure.retry_count += 1
        self._save_closures()

    def to_dict(self, closure_id: str) -> dict:
        """Return closure as dict for API response."""
        closure = self._record(closure_id).closure
        return {
            "id": closure.id,
            "objective": closure.objective,
            "template_id": closure.template_id,
            "run_id": closure.run_id,
            "goal_id": closure.goal_id,
            "status": closure.status,
            "final_status": closure.status,
            "plan_summary": closure.plan_summary,
            "changed_files": closure.changed_files,
            "commands": closure.commands,
            "command_results": closure.command_results,
            "permission_request_ids": closure.permission_request_ids,
            "retry_count": closure.retry_count,
            "review_summary": closure.review_summary,
            "next_action": closure.next_action,
            "created_at": closure.created_at,
        }

    def list_closures(self) -> list[dict]:
        """List all closures."""
        return [self.to_dict(k) for k in self._store]

    def load(self, closure_id: str) -> TaskClosure | None:
        """Load a closure by id. Returns None if not found."""
        record = self._store.get(closure_id)
        return record.closure if record else None

    def verification_plan(self, closure_id: str) -> dict:
        """Return a verification plan. Does NOT execute commands."""
        closure = self._record(closure_id).closure
        return verification_plan_dict(build_verification_plan(closure))

    def assess_completion(self, closure_id: str) -> dict:
        """Assess completion from recorded evidence only."""
        closure = self._record(closure_id).closure
        return verification_assessment_dict(_assess_completion(closure))

    def update_assessment(self, closure_id: str) -> TaskClosure:
        """Update closure status/next action from evidence only."""
        closure = self._record(closure_id).closure
        assessment = _assess_completion(closure)
        if assessment.status == "waiting_permission":
            closure.status = TaskClosureStatus.WAITING_PERMISSION
            closure.next_action = "等待人工批准"
        elif assessment.status == "stopped":
            closure.next_action = "已达到最大步数，需要重新规划或人工处理"
        elif assessment.status == "missing_evidence":
            closure.next_action = "缺少验证证据"
        elif assessment.status == "needs_repair":
            closure.next_action = assessment.repair_suggestions[0] if assessment.repair_suggestions else "需要修复"
        elif assessment.status == "passed":
            closure.status = TaskClosureStatus.COMPLETED
            closure.next_action = "已完成"
            closure.review_summary = assessment.summary
        self._save_closures()
        return closure

    def propose_execution_items(self, closure_id: str, queue_service) -> list[dict]:
        """Create execution queue items from assessment only; does NOT execute."""
        closure = self._record(closure_id).closure
        plan = build_verification_plan(closure)
        assessment = _assess_completion(closure)
        return [item.to_dict() for item in queue_service.create_from_assessment(closure, plan, assessment)]

    def _record(self, closure_id: str) -> TaskClosureRecord:
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        return record

    def _set_status(self, closure_id: str, target: TaskClosureStatus, event_type: str, payload: dict) -> TaskClosure:
        record = self._record(closure_id)
        previous = record.closure.status
        record.closure.status = target
        record.events.append({"type": event_type, "from": previous, "to": target, **payload, "ts": time.time()})
        self._save_closures()
        return record.closure

    def _loop_target(self, loop_status: str, reason: str) -> TaskClosureStatus:
        if loop_status in ("pending_permission", "pause_for_permission"):
            return TaskClosureStatus.WAITING_PERMISSION
        if loop_status in ("failed", "recoverable_failure"):
            return TaskClosureStatus.FAILED if reason == "terminal_failure" else TaskClosureStatus.REPAIRING
        if loop_status == "terminal_failure":
            return TaskClosureStatus.FAILED
        if loop_status == "max_steps_reached" or reason == "max_steps_reached":
            return TaskClosureStatus.STOPPED
        if loop_status in ("complete", "completed"):
            return TaskClosureStatus.COMPLETED
        return TaskClosureStatus.EXECUTING

    def _restore(self, records: list[dict]) -> None:
        for data in records:
            data.pop("events", None)
            closure = TaskClosure(**{k: data.get(k) for k in ["id","objective","template_id","run_id","goal_id","status","plan_summary","changed_files","commands","command_results","permission_request_ids","retry_count","review_summary","next_action","created_at"]})
            self._store[closure.id] = TaskClosureRecord(closure=closure, events=data.get("events", []))

    def _save_closures(self) -> None:
        if self._audit_store is not None:
            records = [{**record.closure.__dict__, "events": record.events} for record in self._store.values()]
            self._audit_store.save_closure_records(records)
