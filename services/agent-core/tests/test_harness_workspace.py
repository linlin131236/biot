from bolt_core.harness import Harness
from bolt_core.tool_protocol import ToolRequest


def test_harness_run_can_override_default_workspace_for_reads(tmp_path):
    default_workspace = tmp_path / "default"
    run_workspace = tmp_path / "project"
    default_workspace.mkdir()
    run_workspace.mkdir()
    target = run_workspace / "README.md"
    target.write_text("project readme", encoding="utf-8")
    harness = Harness(workspace=str(default_workspace))
    run = harness.create_run(goal="read project", workspace=str(run_workspace))
    request = ToolRequest.create("file.read", "read", {"path": str(target)})

    result = harness.submit_tool_request(run.id, request)

    assert run.workspace == str(run_workspace)
    assert result.status == "executed"
    assert "project readme" in (result.output or "")


def test_harness_run_workspace_blocks_other_projects(tmp_path):
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_a.mkdir()
    project_b.mkdir()
    outside = project_b / "README.md"
    outside.write_text("wrong project", encoding="utf-8")
    harness = Harness(workspace=str(project_a))
    run = harness.create_run(goal="read project a", workspace=str(project_a))
    request = ToolRequest.create("file.read", "read", {"path": str(outside)})

    result = harness.submit_tool_request(run.id, request)

    assert result.status == "denied"
    assert harness.p0_context()["unresolved_failures"][0]["tool"] == "file.read"
