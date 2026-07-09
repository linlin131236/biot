from bolt_core.agent_loop import AgentLoop
from bolt_core.model_gateway import ModelConfig, ModelMessage, ModelRequest, ModelResponse, TokenUsage
from bolt_core.tool_protocol import ToolResult
from bolt_core.trace import TraceLog


def test_agent_loop_compresses_large_plain_context_before_gateway_call():
    class LargePlanner:
        def build_request(self, context, config):
            messages = [ModelMessage("user", f"context chunk {index}") for index in range(16)]
            return ModelRequest(messages, config)

    class InspectingGateway:
        def complete(self, request):
            assert len(request.messages) < 16
            assert any("Context summary" in message.content for message in request.messages)
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    trace = TraceLog("run_test")
    loop = AgentLoop(gateway=InspectingGateway(), planner=LargePlanner())

    result = loop.run_loop(
        "summarize",
        ModelConfig("fake", "http://localhost", None, "fake-model"),
        lambda: {},
        trace,
        lambda request: ToolResult(request.id, "executed", "ok"),
        lambda: [],
        max_steps=1,
    )

    assert result.status == "completed"
    assert any(event.type == "context.compressed" for event in trace.events())


# ── P1 regression: no fallback to original when budget too tight for summary ──

def test_agent_loop_drops_older_context_when_budget_too_tight_for_summary():
    """When the budget is too tight to produce a summary, older plain messages
    must be silently dropped — the loop must NOT fall back to the full original
    context (which was the bug: summary is None → return messages)."""

    class _TinyBudgetContext:
        token_budget = 60   # fits ~2 messages of 100 chars; not enough for a summary
        memory_context = []

    class _TinyBudgetBuilder:
        def build(self, goal, p0_context, events, memories):
            return _TinyBudgetContext()

    class _BigPlanner:
        def build_request(self, context, config):
            # 10 messages × ~108 chars ≈ 270 tokens total; budget=60 → only 2 fit
            msgs = [
                ModelMessage("user", f"chunk_{i}_" + "x" * 100)
                for i in range(10)
            ]
            return ModelRequest(msgs, config)

    received_counts: list[int] = []

    class _RecordingGateway:
        def complete(self, request):
            received_counts.append(len(request.messages))
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    trace = TraceLog("run_test_tiny_budget")
    loop = AgentLoop(
        gateway=_RecordingGateway(),
        planner=_BigPlanner(),
        context_builder=_TinyBudgetBuilder(),
    )

    result = loop.run_loop(
        "test",
        ModelConfig("fake", "http://localhost", None, "fake-model"),
        lambda: {},
        trace,
        lambda request: ToolResult(request.id, "executed", "ok"),
        lambda: [],
        max_steps=1,
    )

    assert result.status == "completed"

    # Core assertion: loop must NOT have sent all 10 original messages
    assert len(received_counts) >= 1
    assert received_counts[0] < 10, (
        f"loop sent {received_counts[0]} messages to model; expected < 10. "
        "Falling back to original context when summary is None is the bug."
    )

    # context.compressed must be recorded regardless of whether a summary exists
    compressed_events = [e for e in trace.events() if e.type == "context.compressed"]
    assert compressed_events, "context.compressed trace event must be recorded"
    assert compressed_events[0].payload["compressed_messages"] > 0
