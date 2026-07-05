from bolt_core.document_gardener import failure_pattern_markdown, failure_pattern_path
from bolt_core.failure_memory import ToolFailure
from bolt_core.harness import Harness


def test_failure_pattern_renderer_uses_stable_sections():
    failure = ToolFailure("shell.execute", "command", "execution_failed", "pytest failed", "missing dependency", "not_fixed")

    markdown = failure_pattern_markdown(failure, source="tool_123")

    assert markdown.startswith("# shell.execute command execution_failed")
    assert "## Trigger" in markdown
    assert "## Symptom" in markdown
    assert "pytest failed" in markdown
    assert "## Do Not Repeat" in markdown
    assert "tool_123" in markdown


def test_failure_pattern_path_is_stable_and_scoped_to_docs():
    failure = ToolFailure("file.read", "read", "permission_denied", "secret path denied", "secret path denied", "not_fixed")

    path = failure_pattern_path("C:/Projects/Bolt", failure)

    assert path.replace("\\", "/").endswith("docs/failure-patterns/file-read-permission-denied.md")


def test_document_gardener_queues_file_write_without_direct_write(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="garden docs")
    failure = ToolFailure("shell.execute", "command", "execution_failed", "pytest failed", "missing dependency", "not_fixed")
    harness.memory.record_failure(failure, source="tool_123")

    result = harness.run_document_gardener(run.id)
    pending = harness.pending_permissions()[0]
    proposed_path = pending.payload["path"]

    assert result.status == "pending_permission"
    assert pending.tool == "file.write"
    assert "docs/failure-patterns" in proposed_path.replace("\\", "/")
    assert not (workspace / "docs" / "failure-patterns" / "shell-execute-command-execution-failed.md").exists()
    assert "maintenance.document_gardener.proposed" in [event.type for event in harness.trace(run.id)]
