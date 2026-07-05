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


def _fixed_gateway(path, tool="file.read", payload=None):
    class Gateway:
        def complete(self, request):
            body = payload or {"path": path}
            content = '{"tool":"' + tool + '","operation":"' + ("write" if tool == "file.write" else "read") + '","payload":' + __import__("json").dumps(body) + "}"
            return ModelResponse("completed", content, TokenUsage(2, 3, 5), None)

    return Gateway()


def _has_trace(harness: Harness, run_id: str, event_type: str) -> bool:
    return any(event.type == event_type for event in harness.trace(run_id))
