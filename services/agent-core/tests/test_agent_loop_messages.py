from bolt_core.agent_loop import AgentLoop
from bolt_core.harness import Harness
from bolt_core.model_gateway import ModelResponse, TokenUsage, ToolCall


def test_agent_loop_uses_tool_role_messages_for_next_model_call(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("tool role output", encoding="utf-8")

    class ToolRoleGateway:
        def __init__(self):
            self.calls = 0

        def complete(self, request):
            self.calls += 1
            if self.calls == 1:
                return ModelResponse("completed", None, TokenUsage(1, 1, 2), [ToolCall("call_read", "file.read", {"path": str(readme)})], None)
            tool_messages = [message for message in request.messages if message.role == "tool"]
            assert len(tool_messages) == 1
            assert "tool role output" in tool_messages[0].content
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    gateway = ToolRoleGateway()
    harness = Harness(workspace=str(workspace))
    harness.agent_loop = AgentLoop(gateway=gateway)
    harness.model_settings.update({"provider": "fake", "base_url": "http://localhost", "model": "fake-model"})
    run = harness.create_run("read then summarize")

    result = harness.run_agent_loop(run.id, max_steps=2)

    assert result.status == "completed"
    assert gateway.calls == 2


def test_agent_loop_submits_all_tool_calls_from_one_model_response(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    first = workspace / "first.txt"
    second = workspace / "second.txt"
    first.write_text("first output", encoding="utf-8")
    second.write_text("second output", encoding="utf-8")

    class MultiToolGateway:
        def complete(self, request):
            tool_messages = [message.content for message in request.messages if message.role == "tool"]
            if not tool_messages:
                return ModelResponse("completed", None, TokenUsage(1, 1, 2), [
                    ToolCall("call_first", "file.read", {"path": str(first)}),
                    ToolCall("call_second", "file.read", {"path": str(second)}),
                ], None)
            assert any("first output" in message for message in tool_messages)
            assert any("second output" in message for message in tool_messages)
            return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)

    harness = Harness(workspace=str(workspace))
    harness.agent_loop = AgentLoop(gateway=MultiToolGateway())
    harness.model_settings.update({"provider": "fake", "base_url": "http://localhost", "model": "fake-model"})
    run = harness.create_run("read two files")

    result = harness.run_agent_loop(run.id, max_steps=2)

    assert result.status == "completed"
    observed = [event for event in harness.trace(run.id) if event.type == "tool.result.observed"]
    assert len(observed) == 2


def test_agent_loop_run_loop_stops_on_model_gateway_failure(tmp_path):
    class FailingGateway:
        def __init__(self):
            self.calls = 0

        def complete(self, request):
            self.calls += 1
            return ModelResponse("failed", None, TokenUsage(0, 0, 0), [], "api key missing")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    gateway = FailingGateway()
    harness = Harness(workspace=str(workspace))
    harness.agent_loop = AgentLoop(gateway=gateway)
    harness.model_settings.update({"provider": "fake", "base_url": "http://localhost", "model": "fake-model"})
    run = harness.create_run("read README")

    result = harness.run_agent_loop(run.id, max_steps=50)

    assert result.status == "failed"
    assert result.steps == 1
    assert result.error == "api key missing"
    assert gateway.calls == 1


def test_harness_agent_loop_default_max_steps_is_fifty(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Bolt", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(readme))
    harness.model_settings.update({"provider": "fake", "base_url": "http://localhost", "model": "fake-model"})
    run = harness.create_run("read until bounded")

    result = harness.run_agent_loop(run.id)

    assert result.status == "executed"
    assert result.steps == 50


def _fixed_gateway(path):
    call = ToolCall("call_file_read", "file.read", {"path": path})

    class Gateway:
        def complete(self, request):
            return ModelResponse("completed", None, TokenUsage(2, 3, 5), [call], None)

    return Gateway()
