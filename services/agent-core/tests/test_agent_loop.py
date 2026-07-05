from bolt_core.agent_loop import AgentLoop
from bolt_core.harness import Harness
from bolt_core.model_gateway import ModelResponse, TokenUsage


class BadGateway:
    def complete(self, request):
        return ModelResponse("completed", "not json", TokenUsage(1, 1, 2), None)


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
    harness.agent_loop.gateway = _fixed_gateway(str(target), tool="file.write", payload={"path": str(target), "proposed_content": "new\n"})
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

    assert result.status == "failed"
    assert result.error == "model output is not valid json"
    assert _has_trace(harness, run.id, "agent.step.failed")


def test_agent_loop_denies_unknown_tools(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    harness.agent_loop.gateway = _fixed_gateway(str(workspace), tool="browser.open", operation="open", payload={"url": "https://example.test"})
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
    harness.agent_loop.gateway = _fixed_gateway(str(target), tool="file.write", operation="write", payload={"path": str(target), "proposed_content": "new\n"})
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
    harness.agent_loop.gateway = _fixed_gateway(str(workspace), tool="shell.execute", operation="command", payload={"command": "rm -rf /", "workdir": str(workspace)})
    run = harness.create_run("dangerous")

    result = harness.run_agent_loop(run.id, max_steps=3)

    assert result.status == "denied"
    assert result.steps == 1
    assert _has_trace(harness, run.id, "agent.loop.stopped")


def _fixed_gateway(path, tool="file.read", operation=None, payload=None):
    class Gateway:
        def complete(self, request):
            body = payload or {"path": path}
            op = operation or ("write" if tool == "file.write" else "read")
            content = '{"tool":"' + tool + '","operation":"' + op + '","payload":' + __import__("json").dumps(body) + "}"
            return ModelResponse("completed", content, TokenUsage(2, 3, 5), None)

    return Gateway()


def _has_trace(harness: Harness, run_id: str, event_type: str) -> bool:
    return any(event.type == event_type for event in harness.trace(run_id))
