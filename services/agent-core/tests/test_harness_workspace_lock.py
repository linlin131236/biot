import pytest

from bolt_core.harness import Harness
from bolt_core.tool_protocol import ToolRequest
from bolt_core.workspace_lock import resolve_app_workspace


def test_app_workspace_can_leave_default_unlocked_for_explicit_test_workspaces(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace_root, locked_workspace = resolve_app_workspace(None, None)

    assert workspace_root == tmp_path.resolve()
    assert locked_workspace is None


def test_app_workspace_locks_default_cwd_when_required(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace_root, locked_workspace = resolve_app_workspace(None, None, lock_default=True)

    assert workspace_root == tmp_path.resolve()
    assert locked_workspace == str(tmp_path.resolve())


def test_locked_harness_rejects_run_workspace_outside_lock(tmp_path):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    harness = Harness(workspace=str(project), locked_workspace=str(project))

    with pytest.raises(ValueError, match="workspace outside locked root"):
        harness.create_run(goal="read outside", workspace=str(outside))


def test_locked_harness_allows_run_workspace_inside_lock(tmp_path):
    project = tmp_path / "project"
    nested = project / "packages" / "app"
    nested.mkdir(parents=True)
    target = nested / "README.md"
    target.write_text("nested workspace", encoding="utf-8")
    harness = Harness(workspace=str(project), locked_workspace=str(project))
    run = harness.create_run(goal="read nested", workspace=str(nested))

    result = harness.submit_tool_request(run.id, ToolRequest.create("file.read", "read", {"path": str(target)}))

    assert run.workspace == str(nested.resolve())
    assert result.status == "executed"
    assert "nested workspace" in (result.output or "")
