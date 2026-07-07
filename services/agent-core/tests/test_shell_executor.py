from bolt_core.shell_executor import execute_shell_command
from bolt_core.tool_protocol import ToolRequest


def test_executes_command_inside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(workspace)})

    result = execute_shell_command(request, str(workspace))

    assert result.status == "executed"
    assert "Python" in (result.output or "")
    assert result.error is None


def test_denies_workdir_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(outside)})

    result = execute_shell_command(request, str(workspace))

    assert result.status == "failed"
    assert result.error == "path outside workspace"


def test_reports_nonzero_exit(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = ToolRequest.create("shell.execute", "command", {"command": "python -c \"import sys; sys.exit(3)\"", "workdir": str(workspace)})

    result = execute_shell_command(request, str(workspace))

    assert result.status == "failed"
    assert result.error == "command exited with 3"


def test_times_out_long_command(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = ToolRequest.create(
        "shell.execute",
        "command",
        {"command": "python -c \"import time; time.sleep(2)\"", "workdir": str(workspace), "timeout_seconds": 1},
    )

    result = execute_shell_command(request, str(workspace))

    assert result.status == "failed"
    assert result.error == "command timed out"


def test_rejects_empty_command(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = ToolRequest.create("shell.execute", "command", {"command": "", "workdir": str(workspace)})

    result = execute_shell_command(request, str(workspace))

    assert result.status == "failed"
    assert result.error == "empty command"


def test_rejects_shell_control_syntax(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version && echo unsafe", "workdir": str(workspace)})

    result = execute_shell_command(request, str(workspace))

    assert result.status == "failed"
    assert result.error == "shell control syntax not allowed: &"
