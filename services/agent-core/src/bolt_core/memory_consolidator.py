from dataclasses import dataclass

from bolt_core.memory_store import MemoryRecord, MemoryStore


@dataclass(frozen=True)
class MemoryConsolidationResult:
    created: int
    sources: int


class MemoryConsolidator:
    def consolidate(self, store: MemoryStore) -> MemoryConsolidationResult:
        created = 0
        sources = store.list(status="active")
        for record in sources:
            if self._is_user_preference(record):
                store.record_user("default", record.content, source=record.id)
                created += 1
            elif record.kind == "tool":
                store.record_long_term(record.scope, f"Tool memory: {record.content}", source=record.id)
                created += 1
        return MemoryConsolidationResult(created, len(sources))

    def _is_user_preference(self, record: MemoryRecord) -> bool:
        lowered = record.content.lower()
        return record.kind == "session" and ("喜欢" in record.content or "prefer" in lowered or "tauri" in lowered)
