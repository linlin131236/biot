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
