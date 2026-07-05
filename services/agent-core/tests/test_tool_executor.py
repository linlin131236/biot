import json

from bolt_core.tool_executor import FakeToolExecutor, ReadOnlyToolExecutor
from bolt_core.tool_protocol import ToolRequest


def test_fake_executor_returns_executed_result():
    executor = FakeToolExecutor()
    request = ToolRequest.create("shell.run", "command", {"command": "pnpm test"})

    result = executor.execute(request)

    assert result.request_id == request.id
    assert result.status == "executed"
    assert result.output == "fake execution completed"
    assert result.error is None


def test_fake_executor_can_return_failed_result():
    executor = FakeToolExecutor()
    request = ToolRequest.create("shell.run", "command", {"command": "pnpm test", "fail": True})

    result = executor.execute(request)

    assert result.status == "failed"
    assert result.output is None
    assert result.error == "fake execution failed"


def test_readonly_executor_reads_workspace_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("print('bolt')", encoding="utf-8")
    executor = ReadOnlyToolExecutor(str(workspace))
    request = ToolRequest.create("file.read", "read", {"path": str(target)})

    result = executor.execute(request)

    assert result.status == "executed"
    payload = json.loads(result.output or "{}")
    assert payload["content"] == "print('bolt')"
    assert payload["path"].endswith("app.py")


def test_readonly_executor_denies_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    workspace.mkdir()
    outside.write_text("no", encoding="utf-8")
    executor = ReadOnlyToolExecutor(str(workspace))
    request = ToolRequest.create("file.read", "read", {"path": str(outside)})

    result = executor.execute(request)

    assert result.status == "failed"
    assert result.error == "path outside workspace"


def test_readonly_executor_searches_files(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "app.py").write_text("print('a')", encoding="utf-8")
    executor = ReadOnlyToolExecutor(str(workspace))
    request = ToolRequest.create("files.search", "search", {"query": "app.py", "mode": "name"})

    result = executor.execute(request)

    assert result.status == "executed"
    payload = json.loads(result.output or "{}")
    assert any(hit["path"].endswith("app.py") for hit in payload["hits"])


def test_readonly_executor_runs_shell_execute_inside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = ReadOnlyToolExecutor(str(workspace))
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(workspace)})

    result = executor.execute(request)

    assert result.status == "executed"
    assert "Python" in (result.output or "")


def test_readonly_executor_fails_unknown_tools(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = ReadOnlyToolExecutor(str(workspace))
    request = ToolRequest.create("browser.open", "open", {"url": "https://example.test"})

    result = executor.execute(request)

    assert result.status == "failed"
    assert "browser.open" in result.error


def test_readonly_executor_fails_legacy_shell_run(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = ReadOnlyToolExecutor(str(workspace))
    request = ToolRequest.create("shell.run", "command", {"command": "pnpm test"})

    result = executor.execute(request)

    assert result.status == "failed"
    assert "shell.run" in result.error
