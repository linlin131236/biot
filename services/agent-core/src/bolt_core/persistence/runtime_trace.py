"""Repository-backed runtime trace log used by the production Harness."""

from __future__ import annotations

from threading import Lock
from uuid import uuid4

from bolt_core.trace import TraceEvent, TraceLog


class RepositoryTraceLog(TraceLog):
    """Keep the in-process TraceLog API while durably appending every event."""

    def __init__(self, run_id: str, repository, runtime_session_id: str) -> None:
        super().__init__(run_id)
        self._repository = repository
        self._runtime_session_id = runtime_session_id
        self._lock = Lock()
        for record in repository.list_runtime_events(runtime_session_id):
            self._events.append(
                TraceEvent(
                    run_id,
                    int(record["sequence"]),
                    str(record["type"]),
                    dict(record["payload"]),
                )
            )

    def record(self, event_type: str, payload: dict) -> TraceEvent:
        with self._lock:
            sequence = len(self._events) + 1
            self._repository.append_runtime_event(
                f"re_{uuid4().hex[:20]}",
                self._runtime_session_id,
                sequence,
                event_type,
                payload,
            )
            event = TraceEvent(self.run_id, sequence, event_type, dict(payload))
            self._events.append(event)
            return event
