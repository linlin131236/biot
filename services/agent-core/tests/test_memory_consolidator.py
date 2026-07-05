from bolt_core.memory_consolidator import MemoryConsolidator
from bolt_core.memory_store import MemoryStore


def test_consolidates_session_preference_to_user_memory():
    store = MemoryStore()
    store.record_session("run_1", "我喜欢 Tauri")

    result = MemoryConsolidator().consolidate(store)

    assert result.created == 1
    assert store.list(kind="user")[0].content == "我喜欢 Tauri"


def test_consolidates_tool_memory_to_long_term_memory():
    store = MemoryStore()
    store.record_tool("file.read", "read README successfully")

    result = MemoryConsolidator().consolidate(store)

    assert result.created == 1
    assert "Tool memory" in store.list(kind="long_term")[0].content
