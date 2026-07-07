import pytest
import sqlite3

from bolt_core.failure_memory import ToolFailure
from bolt_core.memory_store import MEMORY_KINDS, MemoryStore


def test_records_all_memory_kinds_with_scope():
    store = MemoryStore()

    for kind in MEMORY_KINDS:
        store.record(kind=kind, scope="repo", content=f"{kind} memory")

    kinds = {record.kind for record in store.list(scope="repo")}
    assert kinds == MEMORY_KINDS


def test_records_tags_metadata_and_timestamps():
    store = MemoryStore()

    record = store.record("project", "repo", "Uses pnpm", tags=["stack"], metadata={"confidence": 1})

    assert record.tags == ["stack"]
    assert record.metadata["confidence"] == 1
    assert record.created_at
    assert record.updated_at


def test_convenience_record_methods():
    store = MemoryStore()

    store.record_session("run_1", "session note")
    store.record_project("repo", "project note")
    store.record_user("user", "user note")
    store.record_tool("tool", "tool note")
    store.record_long_term("global", "long note")

    assert len(store.list(status="active")) == 5


def test_search_and_resolve_memory():
    store = MemoryStore()
    record = store.record_project("repo", "Bolt uses Tauri")
    store.record_user("user", "Prefers pnpm")

    results = store.search("tauri")
    resolved = store.resolve(record.id)

    assert results[0].id == record.id
    assert resolved.status == "resolved"
    assert store.list(status="active")[0].kind == "user"


def test_unknown_memory_kind_is_rejected():
    store = MemoryStore()

    with pytest.raises(ValueError):
        store.record("unknown", "scope", "content")


def test_record_failure_becomes_p0_constraint():
    store = MemoryStore()
    failure = _failure()

    store.record_failure(failure, source="run_1")
    context = store.p0_context()

    assert context["unresolved_failures"][0]["tool"] == "shell.run"
    assert context["hard_constraints"][0].startswith("Do not retry rm -rf /")


def test_snapshot_groups_records_and_p0_context():
    store = MemoryStore()
    store.record(kind="session", scope="run_1", content="User asked for memory layer")

    snapshot = store.snapshot()

    assert snapshot["records"][0]["kind"] == "session"
    assert snapshot["p0_context"] == {"unresolved_failures": [], "hard_constraints": []}


def test_sqlite_store_persists_general_memory(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    MemoryStore(db_path=str(db_path)).record(kind="project", scope="repo", content="Use pnpm", tags=["stack"], metadata={"confidence": 1})

    restored = MemoryStore(db_path=str(db_path)).list(kind="project")[0]

    assert restored.content == "Use pnpm"
    assert restored.tags == ["stack"]
    assert restored.metadata["confidence"] == 1


def test_sqlite_store_persists_resolved_status(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = MemoryStore(db_path=str(db_path))
    record = store.record(kind="project", scope="repo", content="Use pnpm")

    store.resolve(record.id)
    restored = MemoryStore(db_path=str(db_path))

    assert restored.list(status="resolved")[0].id == record.id


def test_sqlite_store_persists_failure_p0_context(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    MemoryStore(db_path=str(db_path)).record_failure(_failure(), source="run_1")

    context = MemoryStore(db_path=str(db_path)).p0_context()

    assert context["unresolved_failures"][0]["tool"] == "shell.run"


def test_sqlite_store_creates_query_indexes(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    MemoryStore(db_path=str(db_path))

    with sqlite3.connect(db_path) as conn:
        indexes = {row[1] for row in conn.execute("pragma index_list(memory_records)").fetchall()}

    assert "idx_memory_records_kind_status" in indexes
    assert "idx_memory_records_scope_status" in indexes
    assert "idx_memory_records_status" in indexes


def test_sqlite_store_filters_search_in_database(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = MemoryStore(db_path=str(db_path))
    matching = store.record("project", "repo", "Biot uses pnpm")
    store.record("project", "repo", "Other note")
    store.record("user", "repo", "Biot uses pnpm")
    store.resolve(matching.id)

    store.record("project", "repo", "Biot uses pnpm actively")
    results = MemoryStore(db_path=str(db_path)).search("pnpm", kind="project", scope="repo", status="active")

    assert [record.content for record in results] == ["Biot uses pnpm actively"]


def _failure() -> ToolFailure:
    return ToolFailure(
        tool="shell.run",
        operation="rm -rf /",
        failure_class="permission_denied",
        observable_result="destructive command denied",
        root_cause="risk gate blocked destructive command",
        repair_result="not_fixed",
    )
