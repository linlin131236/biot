"""Controlled execution handoff records. Records intent only; never executes."""
from __future__ import annotations

import time
from dataclasses import dataclass, replace

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.execution_queue import ExecutionQueueItem
from bolt_core.evidence_redactor import redact
from bolt_core.persistence.repositories import ControlPlaneRepository


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
    permission_request_id: str | None = None
    permission_status: str = "not_requested"
    bridge_error: str = ""
    permission_workspace: str = ""

    def to_dict(self) -> dict:
        return self.__dict__


class ExecutionHandoffService:
    """Creates handoff records only. Does NOT execute commands, approve permissions, create goals, or run loops."""

    def __init__(
        self, store: ExecutionAuditStore | None = None,
        *, repository: ControlPlaneRepository | None = None,
        workspace_id: str | None = None,
    ) -> None:
        if store is not None and repository is not None:
            raise ValueError("handoff persistence backends are mutually exclusive")
        if repository is not None and workspace_id is None:
            raise ValueError("workspace_id is required for repository-backed handoff")
        self._store = store
        self._repository = repository
        self._workspace_id = workspace_id
        self._records: dict[str, ExecutionHandoffRecord] = {}
        self._revisions: dict[str, int] = {}
        self._counter = 0
        if repository is not None:
            self._restore_repository()
        elif store is not None:
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
        self._save_record(record, creating=True)
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
        previous = replace(record)
        record.status = "completed"
        record.result = redact(result)
        record.updated_at = time.time()
        self._persist_or_restore(record, previous)
        return record

    def fail(self, record_id: str, result: str) -> ExecutionHandoffRecord:
        record = self.get_record(record_id)
        self._require_open(record)
        previous = replace(record)
        record.status = "failed"
        record.result = redact(result)
        record.updated_at = time.time()
        self._persist_or_restore(record, previous)
        return record

    def mark_permission_requested(self, record_id: str, permission_request_id: str, permission_status: str, permission_workspace: str = "") -> ExecutionHandoffRecord:
        record = self.get_record(record_id)
        self._require_open(record)
        previous = replace(record)
        record.permission_request_id = permission_request_id
        record.permission_status = permission_status
        if permission_workspace:
            record.permission_workspace = permission_workspace
        record.status = "waiting_permission"
        record.updated_at = time.time()
        self._persist_or_restore(record, previous)
        return record

    def mark_bridge_note(self, record_id: str, bridge_error: str) -> ExecutionHandoffRecord:
        record = self.get_record(record_id)
        self._require_open(record)
        previous = replace(record)
        record.bridge_error = redact(bridge_error)
        record.updated_at = time.time()
        self._persist_or_restore(record, previous)
        return record

    def mark_bridge_failed(self, record_id: str, permission_status: str, bridge_error: str) -> ExecutionHandoffRecord:
        record = self.get_record(record_id)
        self._require_open(record)
        previous = replace(record)
        record.permission_status = permission_status
        record.bridge_error = redact(bridge_error)
        record.status = "failed"
        record.result = redact(bridge_error)
        record.updated_at = time.time()
        self._persist_or_restore(record, previous)
        return record

    def complete_with_permission(self, record_id: str, permission_status: str, result: str) -> ExecutionHandoffRecord:
        record = self.complete(record_id, result)
        previous = replace(record)
        record.permission_status = permission_status
        self._persist_or_restore(record, previous)
        return record

    def fail_with_permission(self, record_id: str, permission_status: str, result: str) -> ExecutionHandoffRecord:
        record = self.fail(record_id, result)
        previous = replace(record)
        record.permission_status = permission_status
        self._persist_or_restore(record, previous)
        return record

    def find_by_permission_request(self, request_id: str) -> ExecutionHandoffRecord | None:
        for record in self._records.values():
            if record.permission_request_id == request_id:
                return record
        return None

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
            data.setdefault("permission_request_id", None)
            data.setdefault("permission_status", "not_requested")
            data.setdefault("bridge_error", "")
            data.setdefault("permission_workspace", "")
            record = ExecutionHandoffRecord(**data)
            self._records[record.id] = record
            self._counter = max(self._counter, _next_counter(record.id, "eh_"))

    def _restore_repository(self) -> None:
        for data in self._repository.list_handoff_records(self._workspace_id):
            record = _record_from_repository(data)
            self._records[record.id] = record
            self._revisions[record.id] = data["revision"]
            self._counter = max(self._counter, _next_counter(record.id, "eh_"))

    def _persist_or_restore(
        self, record: ExecutionHandoffRecord, previous: ExecutionHandoffRecord,
    ) -> None:
        try:
            self._save_record(record)
        except Exception:
            record.__dict__.update(previous.__dict__)
            raise

    def _save_record(self, record: ExecutionHandoffRecord, *, creating: bool = False) -> None:
        if self._repository is None:
            self._records[record.id] = record
            self._save()
            return
        payload = _record_payload(record)
        revision = self._revisions.get(record.id)
        if creating or revision is None:
            self._repository.create_handoff_record(
                record.id, self._workspace_id, record.queue_item_id,
                record.closure_id, record.status, payload,
            )
            self._revisions[record.id] = 0
        else:
            updated = self._repository.update_handoff_record(
                record.id, revision, record.status, payload,
            )
            self._revisions[record.id] = updated["revision"]
        self._records[record.id] = record

    def _save(self) -> None:
        if self._store is not None:
            self._store.save_handoff_records([record.to_dict() for record in self._records.values()])


def _record_payload(record: ExecutionHandoffRecord) -> dict:
    return record.to_dict()


def _record_from_repository(data: dict) -> ExecutionHandoffRecord:
    payload = dict(data["payload"])
    payload.setdefault("id", data["id"])
    payload.setdefault("queue_item_id", data["queue_item_id"])
    payload.setdefault("closure_id", data["closure_id"])
    payload.setdefault("status", data["status"])
    payload.setdefault("created_at", 0.0)
    payload.setdefault("updated_at", payload["created_at"])
    payload.setdefault("result", "")
    payload.setdefault("run_id", None)
    payload.setdefault("goal_id", None)
    payload.setdefault("permission_request_id", None)
    payload.setdefault("permission_status", "not_requested")
    payload.setdefault("bridge_error", "")
    payload.setdefault("permission_workspace", "")
    return ExecutionHandoffRecord(**payload)


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
