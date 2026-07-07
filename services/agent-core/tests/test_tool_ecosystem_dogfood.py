"""Tests for ToolEcosystemDogfoodService (M110)."""
from pathlib import Path

import pytest

from bolt_core.tool_ecosystem_dogfood import ToolEcosystemDogfoodService


def make_full_project(tmp_path: Path) -> Path:
    """Create minimal project structure for dogfood testing."""
    # Backend source files
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    (src / "tool_registry.py").write_text("# tool registry")
    (src / "tool_manifest.py").write_text("# tool manifest")
    (src / "tool_permission_contract.py").write_text("# tool permission contract")
    (src / "readonly_tool_runner.py").write_text("def _redact(): pass")
    (src / "write_tool_proposal.py").write_text("# write tool proposal")
    (src / "patch_proposal.py").write_text("# patch proposal")
    (src / "approval_apply.py").write_text("# approval apply")
    (src / "test_runner_integration.py").write_text("def _redact(): pass")

    # Backend test files
    tests = tmp_path / "services/agent-core/tests"
    tests.mkdir(parents=True, exist_ok=True)
    for t in ("test_tool_registry", "test_tool_manifest", "test_tool_permission_contract",
              "test_readonly_tool_runner", "test_write_tool_proposal", "test_patch_proposal",
              "test_approval_apply", "test_test_runner_integration"):
        (tests / f"{t}.py").write_text(f"# {t}")

    # Desktop files
    desktop = tmp_path / "apps/desktop/src"
    desktop.mkdir(parents=True, exist_ok=True)
    (desktop / "PatchPreviewPanel.tsx").write_text("// PatchPreviewPanel")
    (desktop / "PatchPreviewPanel.test.tsx").write_text("// test")

    # Docs — exec plans for all 10 milestones
    exec_plans = tmp_path / "docs/exec-plans/active"
    exec_plans.mkdir(parents=True, exist_ok=True)
    for n in range(101, 111):
        (exec_plans / f"{n}-tool.md").write_text(f"# M{n}")
    # Docs — decisions for all 10 milestones
    decisions = tmp_path / "docs/decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    for n in range(101, 111):
        (decisions / f"{n}-tool.md").write_text(f"# M{n} decision")
    # Docs — review gates for all 10 milestones
    for n in range(101, 111):
        (tmp_path / f"docs/phase-{n}-review-gate.md").write_text(f"# M{n} review gate")

    # project-state
    (tmp_path / "docs/project-state.md").write_text("## M110 完成\nV6 工具生态")

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
