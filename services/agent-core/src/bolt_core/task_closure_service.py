"""TaskClosureService: conservative evidence recorder, no tool execution."""
import time
from dataclasses import dataclass, field
from typing import Optional

from bolt_core.task_closure import (
    TaskClosure, TaskClosureStatus, TaskTemplateId, MAX_RETRIES, can_transition, task_templates,
)


@dataclass
class TaskClosureRecord:
    closure: TaskClosure
    events: list[dict] = field(default_factory=list)


class TaskClosureService:
    """Records task closure evidence. Does NOT execute tools, push, release, or approve permissions."""

    def __init__(self) -> None:
        self._store: dict[str, TaskClosureRecord] = {}
        self._counter: int = 0

    def start(self, objective: str, template_id: TaskTemplateId,
              run_id: Optional[str] = None, goal_id: Optional[str] = None) -> TaskClosure:
        """Create a new task closure record."""
        closure = TaskClosure(
            id=f"cl_{self._counter}",
            objective=objective,
            template_id=template_id,
            run_id=run_id,
            goal_id=goal_id,
            created_at=time.time(),
        )
        self._counter += 1
        self._store[closure.id] = TaskClosureRecord(closure=closure)
        return closure

    def transition(self, closure_id: str, target: TaskClosureStatus) -> TaskClosure:
        """Transition closure to a new status if legal."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        closure = record.closure
        if not can_transition(closure.status, target):
            raise ValueError(f"illegal transition: {closure.status} → {target}")
        previous = closure.status
        closure.status = target
        record.events.append({"type": "transition", "from": previous, "to": target, "ts": time.time()})
        return closure

    def record_command(self, closure_id: str, command: str, result: str) -> None:
        """Record a verification command and its result."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        record.closure.commands.append(command)
        record.closure.command_results.append(result)
        record.events.append({"type": "command", "command": command, "result": result, "ts": time.time()})

    def record_file_change(self, closure_id: str, file_path: str) -> None:
        """Record a changed file."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        record.closure.changed_files.append(file_path)
        record.events.append({"type": "file_change", "path": file_path, "ts": time.time()})

    def record_permission(self, closure_id: str, permission_id: str) -> None:
        """Record a permission request ID."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        record.closure.permission_request_ids.append(permission_id)
        record.events.append({"type": "permission", "id": permission_id, "ts": time.time()})

    def record_review(self, closure_id: str, summary: str, passed: bool) -> TaskClosure:
        """Record a review summary."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        record.closure.review_summary = summary
        record.closure.next_action = "合并到 main" if passed else "需要人工处理"
        record.events.append({"type": "review", "summary": summary, "passed": passed, "ts": time.time()})
        return record.closure

    def should_stop_repairing(self, closure_id: str) -> bool:
        """Check if repair retries have exceeded MAX_RETRIES."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        return record.closure.retry_count >= MAX_RETRIES

    def increment_retry(self, closure_id: str) -> None:
        """Increment retry count."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        record.closure.retry_count += 1

    def to_dict(self, closure_id: str) -> dict:
        """Return closure as dict for API response."""
        record = self._store.get(closure_id)
        if record is None:
            raise ValueError(f"closure {closure_id} not found")
        return {
            "id": record.closure.id,
            "objective": record.closure.objective,
            "template_id": record.closure.template_id,
            "run_id": record.closure.run_id,
            "goal_id": record.closure.goal_id,
            "status": record.closure.status,
            "final_status": record.closure.status,
            "plan_summary": record.closure.plan_summary,
            "changed_files": record.closure.changed_files,
            "commands": record.closure.commands,
            "command_results": record.closure.command_results,
            "permission_request_ids": record.closure.permission_request_ids,
            "retry_count": record.closure.retry_count,
            "review_summary": record.closure.review_summary,
            "next_action": record.closure.next_action,
            "created_at": record.closure.created_at,
        }

    def list_closures(self) -> list[dict]:
        """List all closures."""
        return [self.to_dict(k) for k in self._store]

    def load(self, closure_id: str) -> TaskClosure | None:
        """Load a closure by id. Returns None if not found."""
        record = self._store.get(closure_id)
        return record.closure if record else None
