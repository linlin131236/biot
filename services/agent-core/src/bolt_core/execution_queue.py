"""Human approval execution queue. Records actions only; never executes."""
from __future__ import annotations

import time
from dataclasses import dataclass, replace

from bolt_core.execution_audit_store import ExecutionAuditStore
from bolt_core.persistence.repositories import ControlPlaneRepository
from bolt_core.task_closure import TaskClosure
from bolt_core.task_verification import VerificationAssessment, VerificationPlan


class ExecutionQueueItemNotFound(ValueError):
    pass


class ExecutionQueueInvalidTransition(ValueError):
    pass


@dataclass
class ExecutionQueueItem:
    id: str
    closure_id: str
    kind: str
    title: str
    description: str
    risk: str
    status: str
    command: str | None
    reason: str
    result: str
    created_at: float

    def to_dict(self) -> dict:
        return self.__dict__


class ExecutionQueueService:
    """Stores human-approved actions. Does NOT execute commands or approve permissions."""

    def __init__(
        self, store: ExecutionAuditStore | None = None,
        *, repository: ControlPlaneRepository | None = None,
        workspace_id: str | None = None,
    ) -> None:
        if store is not None and repository is not None:
            raise ValueError("queue persistence backends are mutually exclusive")
        if repository is not None and workspace_id is None:
            raise ValueError("workspace_id is required for repository-backed queue")
        self._store = store
        self._repository = repository
        self._workspace_id = workspace_id
        self._items: dict[str, ExecutionQueueItem] = {}
        self._revisions: dict[str, int] = {}
        self._counter = 0
        if repository is not None:
            self._restore_repository()
        elif store is not None:
            self._restore(store.load().queue_items)

    def create_item(self, closure_id: str, kind: str, title: str, description: str,
                    risk: str, command: str | None = None, reason: str = "") -> ExecutionQueueItem:
        existing = self._pending_duplicate(closure_id, kind, title, command)
        if existing is not None:
            return existing
        item = ExecutionQueueItem(
            id=f"eq_{self._counter}", closure_id=closure_id, kind=kind,
            title=title, description=description, risk=risk, status="pending",
            command=command, reason=reason, result="", created_at=time.time(),
        )
        if self._repository is not None:
            self._save_item(item, creating=True)
        else:
            self._items[item.id] = item
            self._save()
        self._counter += 1
        return item

    def list_items(self, closure_id: str | None = None) -> list[ExecutionQueueItem]:
        items = list(self._items.values())
        if closure_id is None:
            return items
        return [item for item in items if item.closure_id == closure_id]

    def get_item(self, item_id: str) -> ExecutionQueueItem:
        item = self._items.get(item_id)
        if item is None:
            raise ExecutionQueueItemNotFound(f"execution queue item {item_id} not found")
        return item

    def approve(self, item_id: str) -> ExecutionQueueItem:
        item = self.get_item(item_id)
        if item.status != "pending":
            raise ExecutionQueueInvalidTransition(f"cannot approve item in status {item.status}")
        previous = replace(item)
        item.status = "approved"
        self._persist_or_restore(item, previous)
        return item

    def reject(self, item_id: str, reason: str) -> ExecutionQueueItem:
        item = self.get_item(item_id)
        if item.status != "pending":
            raise ExecutionQueueInvalidTransition(f"cannot reject item in status {item.status}")
        previous = replace(item)
        item.status = "rejected"
        item.reason = reason
        self._persist_or_restore(item, previous)
        return item

    def mark_completed(self, item_id: str, result: str) -> ExecutionQueueItem:
        item = self.get_item(item_id)
        if item.status == "pending" and item.risk not in ("read_only",) and item.kind != "manual_review":
            raise ExecutionQueueInvalidTransition("pending item requires approval before completion")
        if item.status not in ("pending", "approved"):
            raise ExecutionQueueInvalidTransition(f"cannot complete item in status {item.status}")
        previous = replace(item)
        item.status = "completed"
        item.result = result
        self._persist_or_restore(item, previous)
        return item

    def mark_failed(self, item_id: str, result: str) -> ExecutionQueueItem:
        item = self.get_item(item_id)
        if item.status != "approved":
            raise ExecutionQueueInvalidTransition(f"cannot fail item in status {item.status}")
        previous = replace(item)
        item.status = "failed"
        item.result = result
        self._persist_or_restore(item, previous)
        return item

    def create_from_assessment(self, closure: TaskClosure, plan: VerificationPlan,
                               assessment: VerificationAssessment) -> list[ExecutionQueueItem]:
        if assessment.status == "passed":
            return []
        if assessment.status == "waiting_permission":
            return [self.create_item(closure.id, "manual_review", "等待人工批准", assessment.summary, "workspace_write")]
        if assessment.status == "stopped":
            return [self.create_item(closure.id, "replan", "重新规划任务", assessment.summary, "read_only")]
        if assessment.status == "needs_repair":
            return [self.create_item(closure.id, "repair_suggestion", "处理修复建议", _joined(assessment.repair_suggestions), "workspace_write")]
        return self._missing_evidence_items(closure, plan, assessment)

    def _missing_evidence_items(self, closure: TaskClosure, plan: VerificationPlan,
                                assessment: VerificationAssessment) -> list[ExecutionQueueItem]:
        items: list[ExecutionQueueItem] = []
        for check in plan.checks:
            if not check.required or check.satisfied:
                continue
            if check.command:
                items.append(self.create_item(closure.id, "verification_command", "记录验证命令", check.missing_reason, "verification_command", check.command))
            else:
                items.append(self.create_item(closure.id, "manual_review", "补充验证证据", check.missing_reason or assessment.summary, "read_only"))
        return items

    def _pending_duplicate(self, closure_id: str, kind: str, title: str, command: str | None) -> ExecutionQueueItem | None:
        for item in self._items.values():
            if item.closure_id == closure_id and item.kind == kind and item.title == title and item.command == command and item.status == "pending":
                return item
        return None

    def _restore(self, items: list[dict]) -> None:
        for data in items:
            item = ExecutionQueueItem(**data)
            self._items[item.id] = item
            self._counter = max(self._counter, _next_counter(item.id, "eq_"))

    def _restore_repository(self) -> None:
        for record in self._repository.list_queue_items(self._workspace_id):
            item = _item_from_record(record)
            self._items[item.id] = item
            self._revisions[item.id] = record["revision"]
            self._counter = max(self._counter, _next_counter(item.id, "eq_"))

    def _persist_or_restore(
        self, item: ExecutionQueueItem, previous: ExecutionQueueItem,
    ) -> None:
        try:
            if self._repository is not None:
                self._save_item(item)
            else:
                self._save()
        except Exception:
            item.__dict__.update(previous.__dict__)
            raise

    def _save_item(self, item: ExecutionQueueItem, *, creating: bool = False) -> None:
        if self._repository is None:
            self._items[item.id] = item
            self._save()
            return
        payload = _item_payload(item)
        revision = self._revisions.get(item.id)
        if creating or revision is None:
            self._repository.create_queue_item(
                item.id, self._workspace_id, item.status, payload,
            )
            self._revisions[item.id] = 0
        else:
            updated = self._repository.update_queue_item(
                item.id, revision, item.status, payload,
            )
            self._revisions[item.id] = updated["revision"]
        self._items[item.id] = item

    def _save(self) -> None:
        if self._store is not None:
            self._store.save_queue_items([item.to_dict() for item in self._items.values()])


def _item_payload(item: ExecutionQueueItem) -> dict:
    return item.to_dict()


def _item_from_record(record: dict) -> ExecutionQueueItem:
    payload = dict(record["payload"])
    payload.setdefault("id", record["id"])
    payload.setdefault("status", record["status"])
    return ExecutionQueueItem(**payload)


def _next_counter(item_id: str, prefix: str) -> int:
    if not item_id.startswith(prefix):
        return 0
    suffix = item_id.removeprefix(prefix)
    return int(suffix) + 1 if suffix.isdigit() else 0


def _joined(items: list[str]) -> str:
    return "；".join(items) if items else "需要人工处理"
