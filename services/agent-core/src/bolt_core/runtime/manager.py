"""Session ownership and validated event coordination across runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Callable
from uuid import uuid4

from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime.events import (
    RuntimeEvent,
    RuntimeEventKind,
    RuntimeEventStream,
    TaskLifecycle,
)
from bolt_core.runtime.registry import RuntimeRegistry


@dataclass(frozen=True)
class RuntimeSessionSnapshot:
    session: RuntimeSession
    status: str
    lifecycle: TaskLifecycle
    implementation_version: str
    pid: int | None
    last_heartbeat: datetime
    last_event_sequence: int
    events: tuple[RuntimeEvent, ...]


class RuntimeManager:
    """Route controlled lifecycle calls and reject unowned runtime events."""

    def __init__(
        self, registry: RuntimeRegistry,
        on_session_closed: Callable[[RuntimeSession], None] | None = None,
    ) -> None:
        self._registry = registry
        self._on_session_closed = on_session_closed or (lambda _session: None)
        self._closed_sessions: set[str] = set()
        self._streams: dict[str, RuntimeEventStream] = {}
        self._sessions: dict[str, RuntimeSession] = {}
        self._lock = RLock()

    def start(self, runtime_id: str, task_id: str, request: dict) -> RuntimeSession:
        runtime = self._registry.resolve(runtime_id)
        session = runtime.start(task_id, request)
        if session.runtime_id != runtime_id or session.task_id != task_id:
            raise ValueError("runtime returned a session with unexpected identity")
        with self._lock:
            if session.session_id in self._sessions:
                raise ValueError("runtime returned a duplicate session")
            self._sessions[session.session_id] = session
            self._streams[session.session_id] = RuntimeEventStream(
                session.task_id, session.runtime_id, session.session_id
            )
        return session

    def send(self, session: RuntimeSession, message: dict) -> None:
        self._runtime_for(session).send(session, message)

    def resume(self, session: RuntimeSession) -> None:
        self._runtime_for(session).resume(session)

    def resolve_approval(self, session: RuntimeSession, approval_id: str, approved: bool) -> None:
        self._runtime_for(session).resolve_approval(session, approval_id, approved)

    def cancel(self, session: RuntimeSession) -> None:
        runtime = self._runtime_for(session)
        self._notify_closed(session)
        runtime.cancel(session)

    def close(self, session: RuntimeSession) -> None:
        runtime = self._runtime_for(session)
        self._notify_closed(session)
        runtime.close(session)

    def sessions(self, *, include_closed: bool = False) -> tuple[RuntimeSession, ...]:
        with self._lock:
            sessions = tuple(self._sessions.values())
            if include_closed:
                return sessions
            return tuple(
                session for session in sessions if session.session_id not in self._closed_sessions
            )

    def shutdown(self) -> None:
        for session in self.sessions(include_closed=True):
            try:
                self.close(session)
            except Exception:
                # Shutdown containment continues even if an individual adapter
                # cannot complete its graceful close protocol.
                self._notify_closed(session)

    def append_event(self, session: RuntimeSession, event: RuntimeEvent) -> None:
        stream = self._stream_for(session)
        stream.append(event)
        if stream.lifecycle is not TaskLifecycle.RUNNING:
            self._notify_closed(session)

    def mark_crashed(self, session: RuntimeSession) -> None:
        stream = self._stream_for(session)
        active = stream.in_flight()
        event = RuntimeEvent(
            event_id=f"evt_{uuid4().hex}",
            task_id=session.task_id,
            runtime_id=session.runtime_id,
            session_id=session.session_id,
            sequence=len(stream.events()) + 1,
            timestamp=datetime.now(UTC),
            kind=RuntimeEventKind.FAILED,
            payload={
                "error_code": "crashed",
                "abandoned_tool_ids": active["tool_ids"],
                "abandoned_approval_ids": active["approval_ids"],
            },
        )
        stream.append(event)
        self._notify_closed(session)

    def snapshot(self, session: RuntimeSession) -> RuntimeSessionSnapshot:
        stream = self._stream_for(session)
        runtime = self._runtime_for(session)
        events = tuple(stream.events())
        status = _status_for(stream.lifecycle, events)
        pid = _runtime_pid(runtime, session)
        return RuntimeSessionSnapshot(
            session=session,
            status=status,
            lifecycle=stream.lifecycle,
            implementation_version=runtime.descriptor.implementation_version,
            pid=pid,
            last_heartbeat=datetime.now(UTC),
            last_event_sequence=len(events),
            events=events,
        )

    def _notify_closed(self, session: RuntimeSession) -> None:
        with self._lock:
            if session.session_id in self._closed_sessions:
                return
            self._closed_sessions.add(session.session_id)
        self._on_session_closed(session)

    def _runtime_for(self, session: RuntimeSession):
        self._stream_for(session)
        return self._registry.resolve(session.runtime_id)

    def _stream_for(self, session: RuntimeSession) -> RuntimeEventStream:
        if not isinstance(session, RuntimeSession):
            raise ValueError("session must be RuntimeSession")
        with self._lock:
            owned = self._sessions.get(session.session_id)
            if owned != session:
                raise ValueError("unknown runtime session")
            return self._streams[session.session_id]


def _runtime_pid(runtime: object, session: RuntimeSession) -> int | None:
    provider = getattr(runtime, "runtime_pid", None)
    return provider(session) if callable(provider) else None


def _status_for(lifecycle: TaskLifecycle, events: tuple[RuntimeEvent, ...]) -> str:
    if lifecycle is not TaskLifecycle.RUNNING:
        return lifecycle.value
    if not events:
        return "starting"
    last = events[-1]
    if last.kind is RuntimeEventKind.STATUS:
        return str(last.payload["status"])
    return "running"
