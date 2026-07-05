from bolt_core.agent_loop import AgentLoop
from bolt_core.harness import Harness
from bolt_core.model_gateway import ModelResponse, TokenUsage, ToolCall


class BadGateway:
    def complete(self, request):
        return ModelResponse("completed", "not json", TokenUsage(1, 1, 2), [], None)


def test_agent_loop_submits_read_tool_through_harness(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Bolt", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(readme))
    run = harness.create_run("read README")

    result = harness.run_agent_step(run.id)

    assert result.status == "executed"
    assert "Bolt" in (result.tool_result.output or "")
    assert _has_trace(harness, run.id, "tokens.recorded")
    assert _has_trace(harness, run.id, "agent.step.completed")


def test_agent_loop_write_request_stops_on_pending_permission(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("old\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(target), tool="file.write", args={"path": str(target), "proposed_content": "new\n"})
    run = harness.create_run("write README")

    result = harness.run_agent_step(run.id)

    assert result.status == "pending_permission"
    assert harness.pending_permissions()[0].tool == "file.write"
    assert target.read_text(encoding="utf-8") == "old\n"


def test_agent_loop_fails_invalid_model_output(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    harness.agent_loop = AgentLoop(gateway=BadGateway())
    run = harness.create_run("bad output")

    result = harness.run_agent_step(run.id)

    assert result.status == "completed"
    assert result.model_output == "not json"


def test_agent_loop_denies_unknown_tools(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(workspace), tool="browser.open", args={"url": "https://example.test"})
    run = harness.create_run("open browser")

    result = harness.run_agent_step(run.id)

    assert result.status == "denied"
    assert result.tool_result.reason == "unknown tool: browser.open"
    assert not any(event.type == "tool.execution.started" for event in harness.trace(run.id))


def test_agent_loop_run_loop_stops_on_pending_permission(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("old\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(target), tool="file.write", args={"path": str(target), "proposed_content": "new\n"})
    run = harness.create_run("write README")

    result = harness.run_agent_loop(run.id, max_steps=3)

    assert result.status == "pending_permission"
    assert result.steps == 1
    assert harness.pending_permissions()[0].tool == "file.write"
    assert _has_trace(harness, run.id, "agent.loop.paused")


def test_agent_loop_run_loop_is_bounded(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Bolt", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(readme))
    run = harness.create_run("read repeatedly")

    result = harness.run_agent_loop(run.id, max_steps=2)

    assert result.status == "executed"
    assert result.steps == 2
    assert _has_trace(harness, run.id, "agent.loop.max_steps_reached")


def test_agent_loop_run_loop_stops_on_denied(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(workspace), tool="shell.execute", args={"command": "rm -rf /", "workdir": str(workspace)})
    run = harness.create_run("dangerous")

    result = harness.run_agent_loop(run.id, max_steps=3)

    assert result.status == "denied"
    assert result.steps == 1
    assert _has_trace(harness, run.id, "agent.loop.stopped")


def test_agent_loop_stops_when_no_tool_call(tmp_path):
    """Model returns text only (no tool_calls) → loop ends with completed."""

    class TextOnlyGateway:
        def complete(self, request):
            return ModelResponse("completed", "Task is done!", TokenUsage(1, 1, 2), [], None)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    harness.agent_loop = AgentLoop(gateway=TextOnlyGateway())
    run = harness.create_run("summarize project")

    result = harness.run_agent_step(run.id)

    assert result.status == "completed"
    assert result.tool_result is None
    assert result.model_output == "Task is done!"


def _fixed_gateway(path, tool="file.read", args=None):
    call_id = f"call_{tool.replace('.', '_')}"
    arguments = args or {"path": path}
    call = ToolCall(call_id, tool, arguments)

    class Gateway:
        def complete(self, request):
            return ModelResponse("completed", None, TokenUsage(2, 3, 5), [call], None)

    return Gateway()


def _has_trace(harness: Harness, run_id: str, event_type: str) -> bool:
    return any(event.type == event_type for event in harness.trace(run_id))
