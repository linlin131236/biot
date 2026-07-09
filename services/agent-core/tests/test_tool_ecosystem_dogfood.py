"""Tests for ToolEcosystemDogfoodService (M110)."""
from pathlib import Path

import pytest

from bolt_core.tool_ecosystem_dogfood import ToolEcosystemDogfoodService


def write_utf8(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def make_full_project(tmp_path: Path) -> Path:
    """Create minimal project structure for dogfood testing."""
    # Backend source files
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    write_utf8(src / "tool_registry.py", "# tool registry")
    write_utf8(src / "tool_manifest.py", "# tool manifest")
    write_utf8(src / "tool_permission_contract.py", "# tool permission contract")
    write_utf8(src / "readonly_tool_runner.py", "def _redact(): pass")
    write_utf8(src / "write_tool_proposal.py", "# write tool proposal")
    write_utf8(src / "patch_proposal.py", "# patch proposal")
    write_utf8(src / "approval_apply.py", "# approval apply")
    write_utf8(src / "test_runner_integration.py", "def _redact(): pass")

    # Backend test files
    tests = tmp_path / "services/agent-core/tests"
    tests.mkdir(parents=True, exist_ok=True)
    for t in ("test_tool_registry", "test_tool_manifest", "test_tool_permission_contract",
              "test_readonly_tool_runner", "test_write_tool_proposal", "test_patch_proposal",
              "test_approval_apply", "test_test_runner_integration"):
        write_utf8(tests / f"{t}.py", f"# {t}")

    # Desktop files
    desktop = tmp_path / "apps/desktop/src"
    desktop.mkdir(parents=True, exist_ok=True)
    write_utf8(desktop / "PatchPreviewPanel.tsx", "// PatchPreviewPanel")
    write_utf8(desktop / "PatchPreviewPanel.test.tsx", "// test")

    # Docs — exec plans for all 10 milestones
    exec_plans = tmp_path / "docs/exec-plans/active"
    exec_plans.mkdir(parents=True, exist_ok=True)
    for n in range(101, 111):
        write_utf8(exec_plans / f"{n}-tool.md", f"# M{n}")
    # Docs — decisions for all 10 milestones
    decisions = tmp_path / "docs/decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    for n in range(101, 111):
        write_utf8(decisions / f"{n}-tool.md", f"# M{n} decision")
    # Docs — review gates for all 10 milestones
    for n in range(101, 111):
        write_utf8(tmp_path / f"docs/phase-{n}-review-gate.md", f"# M{n} review gate")

    # project-state
    write_utf8(tmp_path / "docs/project-state.md", "## M110 完成\nV6 工具生态")

    return tmp_path


class TestDogfood:
    def test_all_pass_with_full_project(self, tmp_path):
        proj = make_full_project(tmp_path)
        service = ToolEcosystemDogfoodService(project_dir=str(proj))
        result = service.review()
        assert result.all_passed is True
        assert len(result.p1_failures) == 0

    def test_all_17_checks(self, tmp_path):
        proj = make_full_project(tmp_path)
        service = ToolEcosystemDogfoodService(project_dir=str(proj))
        result = service.review()
        assert len(result.checks) == 17

    def test_to_dict(self, tmp_path):
        proj = make_full_project(tmp_path)
        service = ToolEcosystemDogfoodService(project_dir=str(proj))
        result = service.review()
        d = result.to_dict()
        assert d["total"] == 17
        assert "checks" in d
        assert "all_passed" in d

    def test_empty_project_fails_all(self, tmp_path):
        service = ToolEcosystemDogfoodService(project_dir=str(tmp_path))
        result = service.review()
        assert result.all_passed is False
        assert len(result.p1_failures) > 0

    def test_no_m111_boundary(self, tmp_path):
        proj = make_full_project(tmp_path)
        service = ToolEcosystemDogfoodService(project_dir=str(proj))
        result = service.review()
        m111_check = [c for c in result.checks if "M111" in c.name]
        assert len(m111_check) == 1
        assert m111_check[0].passed is True
