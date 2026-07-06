"""M35 Workspace binding tests — relative path resolution, traversal denial, sibling prefix."""
from __future__ import annotations

from pathlib import Path

import pytest

from bolt_core.harness import Harness
from bolt_core.risk import classify_patch, classify_path
from bolt_core.tool_protocol import ToolRequest


@pytest.fixture()
def workspace(tmp_path: Path) -> str:
    """Create a workspace directory with a README.md."""
    ws = tmp_path / "project"
    ws.mkdir()
    (ws / "README.md").write_text("# Hello", encoding="utf-8")
    (ws / "src").mkdir()
    (ws / "src" / "app.ts").write_text("export const x = 1;", encoding="utf-8")
    return str(ws)


@pytest.fixture()
def harness(workspace: str) -> Harness:
    return Harness(workspace=workspace)


class TestRelativePathResolution:
    """Relative paths should resolve inside the run workspace."""

    def test_file_read_relative_path_inside_workspace(self, harness: Harness, workspace: str) -> None:
        run = harness.create_run(goal="read readme", workspace=workspace)
        request = ToolRequest.create("file.read", "read", {"path": "README.md"})
        result = harness.submit_tool_request(run.id, request)
        assert result.status == "executed"
        assert "Hello" in (result.output or "")

    def test_file_read_relative_subdir_path(self, harness: Harness, workspace: str) -> None:
        run = harness.create_run(goal="read source", workspace=workspace)
        request = ToolRequest.create("file.read", "read", {"path": "src/app.ts"})
        result = harness.submit_tool_request(run.id, request)
        assert result.status == "executed"

    def test_file_patch_relative_path_queues_permission(self, harness: Harness, workspace: str) -> None:
        run = harness.create_run(goal="patch readme", workspace=workspace)
        request = ToolRequest.create("file.patch", "patch", {"path": "README.md", "old_string": "# Hello", "new_string": "# World"})
        result = harness.submit_tool_request(run.id, request)
        assert result.status == "pending_permission"


class TestTraversalDenial:
    """Parent traversal and outside paths must be denied."""

    def test_file_read_parent_traversal_denied(self, harness: Harness, workspace: str) -> None:
        run = harness.create_run(goal="traverse", workspace=workspace)
        request = ToolRequest.create("file.read", "read", {"path": "../outside.txt"})
        result = harness.submit_tool_request(run.id, request)
        assert result.status == "denied"

    def test_file_patch_parent_traversal_denied(self, harness: Harness, workspace: str) -> None:
        run = harness.create_run(goal="traverse", workspace=workspace)
        request = ToolRequest.create("file.patch", "patch", {"path": "../outside.txt", "old_string": "x", "new_string": "y"})
        result = harness.submit_tool_request(run.id, request)
        assert result.status == "denied"


class TestSiblingPrefix:
    """Sibling directories sharing a prefix must not pass the workspace check."""

    def test_classify_path_sibling_prefix_denied(self, workspace: str) -> None:
        evil = str(Path(workspace).parent / (Path(workspace).name + "_evil"))
        result = classify_path(evil, workspace, "read")
        assert result.action == "deny"

    def test_classify_patch_sibling_prefix_denied(self, workspace: str) -> None:
        evil = str(Path(workspace).parent / (Path(workspace).name + "_evil") / "secret.txt")
        result = classify_patch(evil, workspace)
        assert result.action == "deny"


class TestSecretPathDenial:
    """Secret paths must be denied even when inside workspace."""

    def test_file_read_env_denied(self, harness: Harness, workspace: str) -> None:
        run = harness.create_run(goal="read secrets", workspace=workspace)
        request = ToolRequest.create("file.read", "read", {"path": ".env"})
        result = harness.submit_tool_request(run.id, request)
        assert result.status == "denied"

    def test_file_patch_env_denied(self, harness: Harness, workspace: str) -> None:
        run = harness.create_run(goal="patch secrets", workspace=workspace)
        request = ToolRequest.create("file.patch", "patch", {"path": ".env", "old_string": "x", "new_string": "y"})
        result = harness.submit_tool_request(run.id, request)
        assert result.status == "denied"
