from bolt_core.harness import Harness
from bolt_core.tool_protocol import ToolRequest


def test_harness_records_trace_for_tool_request(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="check safety")
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(workspace)})

    result = harness.submit_tool_request(run.id, request)

    assert result.status == "pending_permission"
    assert "tool.requested" in _trace_types(harness, run.id)


def test_harness_denies_dangerous_command_and_records_failure(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="delete root")
    request = ToolRequest.create("shell.execute", "command", {"command": "rm -rf /", "workdir": str(workspace)})

    result = harness.submit_tool_request(run.id, request)
    context = harness.p0_context()

    assert result.status == "denied"
    assert context["unresolved_failures"][0]["tool"] == "shell.execute"


def test_harness_approves_pending_permission_and_runs_shell_execute(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="approve command")
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(workspace)})
    harness.submit_tool_request(run.id, request)

    result = harness.approve_permission(request.id)

    assert result.status == "executed"
    assert "Python" in (result.output or "")
    assert harness.pending_permissions() == []
    assert harness.trace(run.id)[-1].type == "tool.execution.completed"


def test_harness_rejects_pending_permission_without_execution(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="reject command")
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(workspace)})
    harness.submit_tool_request(run.id, request)

    result = harness.reject_permission(request.id)

    assert result.status == "rejected"
    assert harness.pending_permissions() == []
    assert harness.trace(run.id)[-1].type == "permission.rejected"


def test_harness_execution_failure_records_memory(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="failing command")
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(outside)})
    harness.submit_tool_request(run.id, request)

    result = harness.approve_permission(request.id)
    context = harness.p0_context()

    assert result.status == "failed"
    assert harness.trace(run.id)[-1].type == "tool.execution.failed"
    assert context["unresolved_failures"][0]["tool"] == "shell.execute"


def test_harness_executes_file_read_immediately_without_permission(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("print('bolt')", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="read file")
    request = ToolRequest.create("file.read", "read", {"path": str(target)})

    result = harness.submit_tool_request(run.id, request)

    assert result.status == "executed"
    assert "print('bolt')" in (result.output or "")
    assert harness.pending_permissions() == []
    assert _trace_types(harness, run.id)[-4:] == ["permission.evaluated", "permission.auto_allowed", "tool.execution.started", "tool.execution.completed"]


def test_harness_executes_files_search_immediately(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "app.py").write_text("print('a')", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="search files")
    request = ToolRequest.create("files.search", "search", {"query": "app.py", "mode": "name"})

    result = harness.submit_tool_request(run.id, request)

    assert result.status == "executed"
    assert "app.py" in (result.output or "")
    assert harness.pending_permissions() == []


def test_harness_denies_file_read_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    workspace.mkdir()
    outside.write_text("no", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="read outside")
    request = ToolRequest.create("file.read", "read", {"path": str(outside)})

    result = harness.submit_tool_request(run.id, request)
    context = harness.p0_context()

    assert result.status == "denied"
    assert context["unresolved_failures"][0]["tool"] == "file.read"


def test_harness_queues_file_write_with_change_set(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="write file")
    request = ToolRequest.create("file.write", "write", {"path": str(target), "proposed_content": "new\n"})

    result = harness.submit_tool_request(run.id, request)
    pending = harness.pending_permissions()[0]

    assert result.status == "pending_permission"
    assert "base_hash" in (result.reason or "")
    assert pending.payload["change_set"]["proposed"] == "new\n"
    assert "change.proposed" in _trace_types(harness, run.id)


def test_harness_approves_file_write_and_applies_change(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="write file")
    request = ToolRequest.create("file.write", "write", {"path": str(target), "proposed_content": "new\n"})
    harness.submit_tool_request(run.id, request)

    result = harness.approve_permission(request.id)

    assert result.status == "executed"
    assert target.read_text(encoding="utf-8") == "new\n"
    assert harness.trace(run.id)[-1].type == "change.applied"


def test_harness_rejects_file_write_without_changing_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="write file")
    request = ToolRequest.create("file.write", "write", {"path": str(target), "proposed_content": "new\n"})
    harness.submit_tool_request(run.id, request)

    result = harness.reject_permission(request.id)

    assert result.status == "rejected"
    assert target.read_text(encoding="utf-8") == "old\n"
    assert harness.trace(run.id)[-1].type == "change.rejected"


def test_harness_fails_file_write_when_base_hash_changes(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="write file")
    request = ToolRequest.create("file.write", "write", {"path": str(target), "proposed_content": "new\n"})
    harness.submit_tool_request(run.id, request)
    target.write_text("user edit\n", encoding="utf-8")

    result = harness.approve_permission(request.id)

    assert result.status == "failed"
    assert result.error == "file changed since proposal"
    assert target.read_text(encoding="utf-8") == "user edit\n"
    assert harness.trace(run.id)[-1].type == "change.failed"


def test_harness_queues_shell_execute_until_approved(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="run command")
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(workspace)})

    result = harness.submit_tool_request(run.id, request)

    assert result.status == "pending_permission"
    assert harness.pending_permissions()[0].tool == "shell.execute"
    assert _trace_types(harness, run.id)[-1] == "permission.pending"


def test_harness_approves_shell_execute_and_records_output(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="run command")
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(workspace)})
    harness.submit_tool_request(run.id, request)

    result = harness.approve_permission(request.id)

    assert result.status == "executed"
    assert "Python" in (result.output or "")
    assert harness.trace(run.id)[-1].type == "tool.execution.completed"


def test_harness_shell_execute_failure_records_memory(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="run outside")
    request = ToolRequest.create("shell.execute", "command", {"command": "python --version", "workdir": str(outside)})
    harness.submit_tool_request(run.id, request)

    result = harness.approve_permission(request.id)
    context = harness.p0_context()

    assert result.status == "failed"
    assert result.error == "path outside workspace"
    assert context["unresolved_failures"][0]["tool"] == "shell.execute"


def test_harness_records_queries_resolves_and_consolidates_memory(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    record = harness.record_memory({"kind": "session", "scope": "run_1", "content": "I prefer Tauri", "tags": ["preference"]})

    queried = harness.query_memory(kind="session", query="tauri")
    result = harness.consolidate_memory()
    resolved = harness.resolve_memory(record.id)

    assert queried[0].id == record.id
    assert resolved.status == "resolved"
    assert result.created >= 1
    assert harness.query_memory(kind="user")[0].content == "I prefer Tauri"


def test_harness_records_perception_memory_when_run_is_created(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")
    harness = Harness(workspace=str(workspace))

    run = harness.create_run(goal="explain project")
    records = harness.query_memory(query="Workspace profile")
    run_records = harness.query_memory(scope=run.id)

    assert records[0].kind == "project"
    assert "workspace_profile" in records[0].tags
    assert run_records[0].metadata["intent"]["category"] == "question"
    assert "perception.snapshot.created" in _trace_types(harness, run.id)
    internal = harness.register_internal_run("run_execution_bridge", "申请人工执行权限")
    assert internal.id == "run_execution_bridge"
    assert len(harness.query_memory(query="Workspace profile")) == 1


def test_harness_prioritizes_perception_memories_for_agent_context(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    for index in range(10):
        harness.record_memory({"kind": "session", "scope": f"old_{index}", "content": f"old memory {index}"})

    harness.create_run(goal="fix bug")
    memories = harness._agent_memories()

    assert memories[0].scope == "workspace_profile"
    assert memories[1].tags == ["perception", "snapshot"]
    assert len(memories) == 8


def _trace_types(harness: Harness, run_id: str) -> list[str]:
    return [event.type for event in harness.trace(run_id)]
