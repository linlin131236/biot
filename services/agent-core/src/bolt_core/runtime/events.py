"""Validated runtime event envelope and fail-closed ordered event stream."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import math
import re
from threading import RLock
from types import MappingProxyType
from typing import Any, Mapping

from bolt_core.runtime.contracts import RuntimeErrorCode, is_runtime_id

_ID = re.compile(r"^[a-z][a-z0-9_-]{2,127}$")
_STATUS_VALUES = frozenset({"starting", "running", "waiting_approval", "recovering"})


class RuntimeEventKind(str, Enum):
    MESSAGE_DELTA = "message_delta"
    THOUGHT = "thought"
    STATUS = "status"
    PLAN_UPDATE = "plan_update"
    TOOL_STARTED = "tool_started"
    TOOL_PROGRESS = "tool_progress"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    FILE_CHANGE = "file_change"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    USAGE_UPDATE = "usage_update"
    CHECKPOINT = "checkpoint"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskLifecycle(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_KINDS = {
    RuntimeEventKind.COMPLETED: TaskLifecycle.COMPLETED,
    RuntimeEventKind.FAILED: TaskLifecycle.FAILED,
    RuntimeEventKind.CANCELLED: TaskLifecycle.CANCELLED,
}
_REQUIRED_PAYLOADS = {
    RuntimeEventKind.STATUS: "status",
    RuntimeEventKind.APPROVAL_REQUESTED: "approval_id",
    RuntimeEventKind.APPROVAL_RESOLVED: "approval_id",
    RuntimeEventKind.TOOL_STARTED: "tool_id",
    RuntimeEventKind.TOOL_PROGRESS: "tool_id",
    RuntimeEventKind.TOOL_COMPLETED: "tool_id",
    RuntimeEventKind.TOOL_FAILED: "tool_id",
    RuntimeEventKind.FILE_CHANGE: "path",
    RuntimeEventKind.COMPLETED: "summary",
    RuntimeEventKind.FAILED: "error_code",
}
_ABANDONMENT_FIELDS = ("abandoned_tool_ids", "abandoned_approval_ids")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("payload object keys must be strings")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("payload must contain JSON-compatible values")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _validated_id_list(payload: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = payload.get(field, ())
    if not isinstance(value, tuple):
        raise ValueError(f"payload {field} must be an array")
    if any(not isinstance(item, str) or not _ID.fullmatch(item) for item in value):
        raise ValueError(f"payload {field} must contain stable identifiers")
    if len(value) != len(set(value)):
        raise ValueError(f"payload {field} cannot contain duplicates")
    return value


@dataclass(frozen=True)
class RuntimeEvent:
    event_id: str
    task_id: str
    runtime_id: str
    session_id: str
    sequence: int
    timestamp: datetime
    kind: RuntimeEventKind
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, RuntimeEventKind):
            raise ValueError("unsupported runtime event")
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be an object")
        for name in ("event_id", "task_id", "session_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _ID.fullmatch(value):
                raise ValueError(f"{name} must be a stable identifier")
        if not is_runtime_id(self.runtime_id):
            raise ValueError("runtime_id must be a stable lowercase identifier")
        if not isinstance(self.timestamp, datetime) or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        object.__setattr__(self, "payload", _freeze_json(self.payload))
        required = _REQUIRED_PAYLOADS.get(self.kind)
        if required and not self.payload.get(required):
            raise ValueError(f"payload requires {required} for {self.kind.value}")
        if self.kind is RuntimeEventKind.STATUS and self.payload["status"] not in _STATUS_VALUES:
            raise ValueError("status must be a supported non-terminal runtime state")
        if self.kind is RuntimeEventKind.FAILED:
            try:
                RuntimeErrorCode(str(self.payload["error_code"]))
            except ValueError as error:
                raise ValueError("error_code must be a RuntimeErrorCode") from error
        if self.kind is RuntimeEventKind.APPROVAL_RESOLVED and not isinstance(self.payload.get("approved"), bool):
            raise ValueError("payload requires boolean approved for approval_resolved")
        for field in ("tool_id", "approval_id"):
            if field in self.payload:
                value = self.payload[field]
                if not isinstance(value, str) or not _ID.fullmatch(value):
                    raise ValueError(f"payload {field} must be a stable identifier")
        for field in _ABANDONMENT_FIELDS:
            if field in self.payload:
                _validated_id_list(self.payload, field)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp.astimezone(UTC).isoformat(),
            "kind": self.kind.value,
            "payload": _thaw_json(self.payload),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RuntimeEvent":
        if not isinstance(value, dict):
            raise ValueError("invalid runtime event envelope")
        try:
            kind = RuntimeEventKind(str(value["kind"]))
        except (KeyError, ValueError) as error:
            raise ValueError("unsupported runtime event") from error
        try:
            raw_timestamp = value["timestamp"]
            if not isinstance(raw_timestamp, str):
                raise ValueError("timestamp must be an ISO-8601 string")
            timestamp = datetime.fromisoformat(raw_timestamp)
            return cls(
                event_id=value["event_id"], task_id=value["task_id"],
                runtime_id=value["runtime_id"], session_id=value["session_id"],
                sequence=value["sequence"], timestamp=timestamp, kind=kind,
                payload=value["payload"],
            )
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, ValueError) and str(error) in {
                "sequence must be a positive integer", "payload must be an object",
            }:
                raise
            raise ValueError("invalid runtime event envelope") from error


class RuntimeEventStream:
    def __init__(self, task_id: str, runtime_id: str, session_id: str) -> None:
        self._task_id = task_id
        self._runtime_id = runtime_id
        self._session_id = session_id
        self._events: list[RuntimeEvent] = []
        self._event_ids: set[str] = set()
        self._active_tools: set[str] = set()
        self._pending_approvals: set[str] = set()
        self._lock = RLock()
        self._lifecycle = TaskLifecycle.RUNNING

    @property
    def lifecycle(self) -> TaskLifecycle:
        return self._lifecycle

    def append(self, event: RuntimeEvent) -> None:
        with self._lock:
            self._validate_identity(event)
            if self._lifecycle is not TaskLifecycle.RUNNING:
                raise ValueError("terminal task cannot accept later events")
            expected = len(self._events) + 1
            if event.sequence != expected:
                raise ValueError(f"sequence must be strictly monotonic: expected {expected}")
            if event.event_id in self._event_ids:
                raise ValueError("event_id must be unique within a runtime session")
            self._validate_terminal_transition(event)
            self._validate_transition(event)
            self._events.append(event)
            self._event_ids.add(event.event_id)
            if event.kind in _TERMINAL_KINDS:
                self._active_tools.clear()
                self._pending_approvals.clear()
                self._lifecycle = _TERMINAL_KINDS[event.kind]

    def events(self) -> list[RuntimeEvent]:
        with self._lock:
            return list(self._events)

    def in_flight(self) -> dict[str, list[str]]:
        with self._lock:
            return {
                "tool_ids": sorted(self._active_tools),
                "approval_ids": sorted(self._pending_approvals),
            }

    def _validate_identity(self, event: RuntimeEvent) -> None:
        for name, expected in (
            ("task_id", self._task_id), ("runtime_id", self._runtime_id), ("session_id", self._session_id),
        ):
            if getattr(event, name) != expected:
                raise ValueError(f"{name} does not match runtime event stream")

    def _validate_terminal_transition(self, event: RuntimeEvent) -> None:
        if event.kind not in _TERMINAL_KINDS:
            return
        if event.kind is RuntimeEventKind.COMPLETED:
            if self._active_tools or self._pending_approvals:
                raise ValueError("completed event cannot leave unresolved tools or approvals")
            return

        abandoned_tools = set(_validated_id_list(event.payload, "abandoned_tool_ids"))
        if abandoned_tools != self._active_tools:
            raise ValueError("abandoned_tool_ids must exactly match active tools")
        abandoned_approvals = set(
            _validated_id_list(event.payload, "abandoned_approval_ids")
        )
        if abandoned_approvals != self._pending_approvals:
            raise ValueError("abandoned_approval_ids must exactly match pending approvals")

    def _validate_transition(self, event: RuntimeEvent) -> None:
        tool_id = event.payload.get("tool_id", "")
        if event.kind is RuntimeEventKind.TOOL_STARTED:
            if tool_id in self._active_tools:
                raise ValueError("tool is already active")
            self._active_tools.add(tool_id)
        elif event.kind in {RuntimeEventKind.TOOL_PROGRESS, RuntimeEventKind.TOOL_COMPLETED, RuntimeEventKind.TOOL_FAILED}:
            if tool_id not in self._active_tools:
                raise ValueError("tool event requires an active tool")
            if event.kind in {RuntimeEventKind.TOOL_COMPLETED, RuntimeEventKind.TOOL_FAILED}:
                self._active_tools.remove(tool_id)

        approval_id = event.payload.get("approval_id", "")
        if event.kind is RuntimeEventKind.APPROVAL_REQUESTED:
            if approval_id in self._pending_approvals:
                raise ValueError("approval is already pending")
            self._pending_approvals.add(approval_id)
        elif event.kind is RuntimeEventKind.APPROVAL_RESOLVED:
            if approval_id not in self._pending_approvals:
                raise ValueError("approval resolution requires a pending approval")
            self._pending_approvals.remove(approval_id)
