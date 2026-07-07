from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class TraceEvent:
    run_id: str
    sequence: int
    type: str
    payload: dict


class TraceLog:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._events: list[TraceEvent] = []
        self._lock = Lock()

    def record(self, event_type: str, payload: dict) -> TraceEvent:
        with self._lock:
            event = TraceEvent(self.run_id, len(self._events) + 1, event_type, payload)
            self._events.append(event)
            return event

    def events(self) -> list[TraceEvent]:
        with self._lock:
            return list(self._events)
