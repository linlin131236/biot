"""Persistent execution audit records. Stores data only; never executes."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


class ExecutionAuditStoreError(ValueError):
    pass


@dataclass
class ExecutionAuditState:
    queue_items: list[dict]
    handoff_records: list[dict]
    closure_records: list[dict] = None

    def __post_init__(self):
        if self.closure_records is None:
            self.closure_records = []


def execution_audit_path(path: str | Path | None, workspace: Path) -> Path:
    if path is not None:
        return Path(path)
    configured = os.environ.get("BOLT_EXECUTION_AUDIT_PATH")
    if configured:
        return Path(configured)
    return workspace / ".bolt" / "execution-audit.json"


class ExecutionAuditStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> ExecutionAuditState:
        if not self._path.exists():
            return ExecutionAuditState(queue_items=[], handoff_records=[], closure_records=[])
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ExecutionAuditStoreError(f"execution audit JSON is damaged: {self._path}") from exc
        if not isinstance(data, dict):
            raise ExecutionAuditStoreError(f"execution audit JSON must be an object: {self._path}")
        queue_items = data.get("queue_items", [])
        handoff_records = data.get("handoff_records", [])
        closure_records = data.get("closure_records", [])
        if not isinstance(queue_items, list) or not isinstance(handoff_records, list) or not isinstance(closure_records, list):
            raise ExecutionAuditStoreError(f"execution audit JSON has invalid lists: {self._path}")
        return ExecutionAuditState(queue_items=queue_items, handoff_records=handoff_records, closure_records=closure_records)

    def save_queue_items(self, queue_items: list[dict]) -> None:
        state = self.load()
        self._save(ExecutionAuditState(queue_items=queue_items, handoff_records=state.handoff_records, closure_records=state.closure_records))

    def save_handoff_records(self, handoff_records: list[dict]) -> None:
        state = self.load()
        self._save(ExecutionAuditState(queue_items=state.queue_items, handoff_records=handoff_records, closure_records=state.closure_records))

    def save_closure_records(self, closure_records: list[dict]) -> None:
        state = self.load()
        self._save(ExecutionAuditState(queue_items=state.queue_items, handoff_records=state.handoff_records, closure_records=closure_records))

    def _save(self, state: ExecutionAuditState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "queue_items": state.queue_items,
            "handoff_records": state.handoff_records,
            "closure_records": state.closure_records,
        }
        tmp_path = self._path.with_name(f"{self._path.name}.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp_path, self._path)
