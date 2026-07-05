from bolt_core.context_builder import ContextBuilder, DEFAULT_TOKEN_BUDGET, MAX_MEMORY_CONTEXT
from bolt_core.memory_store import MemoryStore
from bolt_core.trace import TraceLog


def test_context_builder_includes_goal_memory_trace_and_budget():
    trace = TraceLog("run_1")
    trace.record("run.created", {"goal": "read"})
    p0 = {"unresolved_failures": [], "hard_constraints": ["Do not retry"]}
    memory = MemoryStore().record_project("repo", "Use pnpm")

    packet = ContextBuilder().build("read README", p0, trace.events(), [memory])

    assert packet.goal == "read README"
    assert packet.p0_context["hard_constraints"] == ["Do not retry"]
    assert packet.recent_trace[0]["type"] == "run.created"
    assert packet.token_budget == DEFAULT_TOKEN_BUDGET
    assert packet.memory_context[0]["content"] == "Use pnpm"


def test_context_builder_caps_memory_context():
    store = MemoryStore()
    memories = [store.record_project("repo", f"memory {index}") for index in range(MAX_MEMORY_CONTEXT + 2)]

    packet = ContextBuilder().build("goal", {}, [], memories)

    assert len(packet.memory_context) == MAX_MEMORY_CONTEXT
