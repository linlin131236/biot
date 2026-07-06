"""Controlled execution handoff records. Records intent only; never executes."""
from __future__ import annotations

import time
from dataclasses import dataclass

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.execution_queue import ExecutionQueueItem


class ExecutionHandoffNotFound(ValueError):
    pass


class ExecutionHandoffInvalidTransition(ValueError):
    pass


@dataclass
class ExecutionHandoffRecord:
    id: str
    queue_item_id: str
    closure_id: str
    kind: str
    status: str
    handoff_type: str
    title: str
    instruction: str
    command: str | None
    goal_objective: str
    run_id: str | None
    goal_id: str | None
    created_at: float
    updated_at: float
    result: str

    def to_dict(self) -> dict:
        return self.__dict__


class ExecutionHandoffService:
    """Creates handoff records only. Does NOT execute commands, approve permissions, create goals, or run loops."""

    def __init__(self, store: ExecutionAuditStore | None = None) -> None:
        self._store = store
        self._records: dict[str, ExecutionHandoffRecord] = {}
        self._counter = 0
        if store is not None:
            self._restore(store.load().handoff_records)

    def create_from_queue_item(self, item: ExecutionQueueItem) -> ExecutionHandoffRecord:
        existing = self._find_by_item(item.id)
        if existing is not None:
            return existing
        handoff_type, status, instruction, goal_objective = _handoff_fields(item)
        now = time.time()
        record = ExecutionHandoffRecord(
            id=f"eh_{self._counter}", queue_item_id=item.id, closure_id=item.closure_id,
            kind=item.kind, status=status, handoff_type=handoff_type, title=item.title,
            instruction=instruction, command=item.command, goal_objective=goal_objective,
            run_id=None, goal_id=None, created_at=now, updated_at=now, result="",
        )
        self._counter += 1
        self._records[record.id] = record
        self._save()
        return record

    def list_records(self, closure_id: str | None = None) -> list[ExecutionHandoffRecord]:
        records = list(self._records.values())
        if closure_id is None:
            return records
        return [record for record in records if record.closure_id == closure_id]

    def get_record(self, record_id: str) -> ExecutionHandoffRecord:
        record = self._records.get(record_id)
        if record is None:
            raise ExecutionHandoffNotFound(f"execution handoff {record_id} not found")
        return record

    def complete(self, record_id: str, result: str) -> ExecutionHandoffRecord:
        record = self.get_record(record_id)
        self._require_open(record)
        record.status = "completed"
        record.result = result
        record.updated_at = time.time()
        self._save()
        return record

    def fail(self, record_id: str, result: str) -> ExecutionHandoffRecord:
        record = self.get_record(record_id)
        self._require_open(record)
        record.status = "failed"
        record.result = result
        record.updated_at = time.time()
        self._save()
        return record

    def _find_by_item(self, item_id: str) -> ExecutionHandoffRecord | None:
        for record in self._records.values():
            if record.queue_item_id == item_id:
                return record
        return None

    def _require_open(self, record: ExecutionHandoffRecord) -> None:
        if record.status in ("completed", "failed"):
            raise ExecutionHandoffInvalidTransition(f"cannot update handoff in status {record.status}")

    def _restore(self, records: list[dict]) -> None:
        for data in records:
            record = ExecutionHandoffRecord(**data)
            self._records[record.id] = record
            self._counter = max(self._counter, _next_counter(record.id, "eh_"))

    def _save(self) -> None:
        if self._store is not None:
            self._store.save_handoff_records([record.to_dict() for record in self._records.values()])


def _next_counter(record_id: str, prefix: str) -> int:
    if not record_id.startswith(prefix):
        return 0
    suffix = record_id.removeprefix(prefix)
    return int(suffix) + 1 if suffix.isdigit() else 0


def _handoff_fields(item: ExecutionQueueItem) -> tuple[str, str, str, str]:
    if item.kind == "verification_command":
        return ("manual_verification", "ready_for_manual_action", "请在外部终端人工运行命令，并回来记录结果", "")
    if item.kind == "manual_review" and "等待人工批准" in f"{item.title}{item.description}":
        return ("permission_panel", "waiting_permission", "请到权限面板处理原始权限请求", "")
    if item.kind == "repair_suggestion":
        return ("goal_input", "linked_to_goal", "可复制为目标草稿，但不会自动创建目标", item.description or item.title)
    if item.kind == "replan":
        return ("goal_input", "linked_to_goal", "可复制为重新规划目标草稿，但不会自动创建目标", item.description or "重新规划任务")
    return ("manual_review", "ready_for_manual_action", "请人工处理该队列项", "")
