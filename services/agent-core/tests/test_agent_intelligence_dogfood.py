"""Tests for AgentIntelligenceDogfoodService (M120)."""
from pathlib import Path
import pytest
from bolt_core.agent_intelligence_dogfood import AgentIntelligenceDogfoodService


def write_utf8(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def make_v7_project(tmp_path: Path) -> Path:
    src = tmp_path / "services/agent-core/src/bolt_core"
    src.mkdir(parents=True, exist_ok=True)
    tests = tmp_path / "services/agent-core/tests"
    tests.mkdir(parents=True, exist_ok=True)

    # V7 eval files
    v7_files = ["tool_call_eval", "patch_apply_eval", "test_failure_diagnosis_eval",
                "permission_boundary_eval", "multi_agent_collaboration_eval",
                "memory_retrieval_eval", "chinese_interaction_eval",
                "e2e_task_dogfood", "failure_recovery_dogfood"]
    for f in v7_files:
        write_utf8(src / f"{f}.py", f"# {f}")
        write_utf8(tests / f"test_{f}.py", f"# test_{f}")

    # V6 files
    v6_files = ["tool_registry", "tool_manifest", "tool_permission_contract",
                "readonly_tool_runner", "write_tool_proposal", "patch_proposal",
                "test_runner_integration", "tool_ecosystem_dogfood"]
    for f in v6_files:
        write_utf8(src / f"{f}.py", f"# {f}")
        write_utf8(tests / f"test_{f}.py", f"# test_{f}")
    write_utf8(src / "approval_apply.py", "approved=true\nactor\nhuman\n")
    write_utf8(tests / "test_approval_apply.py", "# test_approval_apply")

    # Docs: exec plans, decisions, review gates for M111-M120
    exec_plans = tmp_path / "docs/exec-plans/active"
    exec_plans.mkdir(parents=True, exist_ok=True)
    decisions = tmp_path / "docs/decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    for n in range(111, 121):
        write_utf8(exec_plans / f"{n}-test.md", f"# M{n}")
        write_utf8(decisions / f"{n}-test.md", f"# M{n}")
        write_utf8(tmp_path / f"docs/phase-{n}-review-gate.md", f"# M{n}")

    write_utf8(tmp_path / "docs/project-state.md", "M120 完成\nV7 智能Agent\n未 push\n未进入 M121")
    return tmp_path


class TestAgentIntelligenceDogfood:
    def test_all_18_checks(self, tmp_path):
        proj = make_v7_project(tmp_path)
        service = AgentIntelligenceDogfoodService(project_dir=str(proj))
        result = service.review()
        assert len(result.checks) == 18, f"需要18项检查，当前{len(result.checks)}"

    def test_all_pass_with_full_project(self, tmp_path):
        proj = make_v7_project(tmp_path)
        service = AgentIntelligenceDogfoodService(project_dir=str(proj))
        result = service.review()
        assert result.all_passed is True, f"P1: {result.p1_failures}"
        assert len(result.p1_failures) == 0

    def test_fails_with_missing_v7_file(self, tmp_path):
        service = AgentIntelligenceDogfoodService(project_dir=str(tmp_path))
        result = service.review()
        assert result.all_passed is False
        assert len(result.p1_failures) > 0

    def test_no_m121_boundary(self, tmp_path):
        proj = make_v7_project(tmp_path)
        service = AgentIntelligenceDogfoodService(project_dir=str(proj))
        result = service.review()
        m121_check = [c for c in result.checks if "M121" in c.name]
        assert len(m121_check) == 1
        assert m121_check[0].passed is True

    def test_to_dict(self, tmp_path):
        proj = make_v7_project(tmp_path)
        service = AgentIntelligenceDogfoodService(project_dir=str(proj))
        result = service.review()
        d = result.to_dict()
        assert d["total"] == 18
        assert d["all_passed"] is True
