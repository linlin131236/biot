from bolt_core.harness import Harness
from bolt_core.tool_protocol import ToolRequest


def test_file_patch_queues_for_permission(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("def hello():\n    print('world')\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="patch file")

    request = ToolRequest.create("file.patch", "patch", {"path": str(target), "old_string": "print('world')", "new_string": "print('bolt')"})
    result = harness.submit_tool_request(run.id, request)

    assert result.status == "pending_permission"
    assert target.read_text(encoding="utf-8") == "def hello():\n    print('world')\n"


def test_file_patch_applies_after_approval(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("def hello():\n    print('world')\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="patch file")

    request = ToolRequest.create("file.patch", "patch", {"path": str(target), "old_string": "print('world')", "new_string": "print('bolt')"})
    harness.submit_tool_request(run.id, request)

    result = harness.approve_permission(request.id)

    assert result.status == "executed"
    assert target.read_text(encoding="utf-8") == "def hello():\n    print('bolt')\n"


def test_file_patch_rejects_non_unique_old_string(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("x = 1\nx = 1\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="patch file")

    request = ToolRequest.create("file.patch", "patch", {"path": str(target), "old_string": "x = 1", "new_string": "x = 2"})
    result = harness.submit_tool_request(run.id, request)

    assert result.status == "denied"
    assert "2 times" in result.reason


def test_file_patch_rejects_missing_old_string(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("hello world\n", encoding="utf-8")
    harness = Harness(workspace=str(workspace))
    run = harness.create_run(goal="patch file")

    request = ToolRequest.create("file.patch", "patch", {"path": str(target), "old_string": "not found", "new_string": "replacement"})
    result = harness.submit_tool_request(run.id, request)

    assert result.status == "denied"
    assert "not found" in result.reason
