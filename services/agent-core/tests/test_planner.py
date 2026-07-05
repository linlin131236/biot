from bolt_core.context_builder import ContextBuilder
from bolt_core.memory_store import MemoryStore
from bolt_core.model_gateway import ModelConfig
from bolt_core.planner import Planner
from bolt_core.trace import TraceLog


def test_planner_prompt_includes_trace_failure_and_perception_metadata():
    trace = TraceLog("run_1")
    trace.record("tool.requested", {"tool": "file.read"})
    p0 = {"hard_constraints": ["Do not retry command"], "unresolved_failures": []}
    store = MemoryStore()
    profile = store.record("project", "workspace_profile", "Workspace profile captured", "test", ["perception", "workspace_profile"], {"package_manager": "pnpm", "languages": ["typescript"]})
    snapshot = store.record("session", "run_1", "Perception snapshot captured", "test", ["perception", "snapshot"], {"intent": {"category": "code_change"}, "scheduler": [{"status": "executed"}]})
    context = ContextBuilder().build("fix bug", p0, trace.events(), [profile, snapshot])

    request = Planner().build_request(context, ModelConfig("fake", "http://localhost", "fake-model", 0.2))
    prompt = request.messages[1].content

    assert "Do not retry command" in prompt
    assert "tool.requested" in prompt
    assert "workspace_profile" in prompt
    assert "pnpm" in prompt
    assert "typescript" in prompt
    assert "code_change" in prompt
