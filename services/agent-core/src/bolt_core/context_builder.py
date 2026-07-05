from dataclasses import dataclass

from bolt_core.memory_store import MemoryRecord
from bolt_core.trace import TraceEvent

DEFAULT_TOKEN_BUDGET = 8000
MAX_MEMORY_CONTEXT = 8


@dataclass(frozen=True)
class ContextPacket:
    goal: str
    p0_context: dict[str, list]
    recent_trace: list[dict]
    token_budget: int
    memory_context: list[dict]


class ContextBuilder:
    def build(self, goal: str, p0_context: dict[str, list], trace: list[TraceEvent], memories: list[MemoryRecord] | None = None) -> ContextPacket:
        recent = [event.__dict__ for event in trace[-10:]]
        memory_context = [_memory_dict(record) for record in (memories or [])[:MAX_MEMORY_CONTEXT]]
        return ContextPacket(goal, p0_context, recent, DEFAULT_TOKEN_BUDGET, memory_context)


def _memory_dict(record: MemoryRecord) -> dict:
    return {"kind": record.kind, "scope": record.scope, "content": record.content, "tags": record.tags}
