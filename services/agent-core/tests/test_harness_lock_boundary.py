from bolt_core.harness import Harness
from bolt_core.tool_protocol import ToolRequest


def test_submit_tool_request_does_not_hold_state_lock_while_executing_tool(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("print('bolt')", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="read file")
    request = ToolRequest.create("file.read", "read", {"path": str(target)})
    original_execute = harness._execute

    def execute_without_state_lock(run_id, tool_request):
        assert not harness._state_lock._is_owned()
        return original_execute(run_id, tool_request)

    harness._execute = execute_without_state_lock

    result = harness.submit_tool_request(run.id, request)

    assert result.status == "executed"
