from dataclasses import dataclass
from threading import RLock

from bolt_core.trace import TraceLog


@dataclass(frozen=True)
class HarnessRun:
    id: str
    goal: str
    workspace: str


class HarnessState:
    def __init__(self) -> None:
        self.runs: dict[str, HarnessRun] = {}
        self.traces: dict[str, TraceLog] = {}
        self.lock = RLock()

    def register(self, run: HarnessRun) -> TraceLog:
        trace = TraceLog(run.id)
        with self.lock:
            self.runs[run.id], self.traces[run.id] = run, trace
        return trace

    def run(self, run_id: str) -> HarnessRun:
        with self.lock:
            return self.runs[run_id]

    def trace(self, run_id: str) -> TraceLog:
        with self.lock:
            return self.traces[run_id]
