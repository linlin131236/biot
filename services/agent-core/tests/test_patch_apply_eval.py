"""Tests for PatchApplyEvalService (M112)."""
from pathlib import Path

import pytest

from bolt_core.patch_apply_eval import (
    PatchApplyEvalCase,
    PatchApplyEvalResult,
    PatchApplyEvalService,
    PatchApplyEvalSummary,
)


class TestPatchApplyEvalCases:
    """评估案例定义测试。"""

    def test_at_least_10_cases(self):
        cases = PatchApplyEvalService._cases()
        assert len(cases) >= 10, f"需要至少10个eval cases，当前{len(cases)}个"

    def test_all_cases_have_unique_ids(self):
        cases = PatchApplyEvalService._cases()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))

    def test_mix_of_success_and_failure(self):
        cases = PatchApplyEvalService._cases()
        success = [c for c in cases if c.expected_success]
        failure = [c for c in cases if not c.expected_success]
        assert len(success) > 0, "需要至少1个成功案例"
        assert len(failure) > 0, "需要至少1个失败案例"

    def test_multi_file_case_exists(self):
        cases = PatchApplyEvalService._cases()
        assert any("multi" in c.case_id for c in cases), "需要多文件案例"

    def test_security_cases_exist(self):
        cases = PatchApplyEvalService._cases()
        blocked = [c for c in cases if "block" in c.case_id]
        assert len(blocked) >= 2, f"需要至少2个路径阻断案例，当前{len(blocked)}个"


class TestPatchApplyEvalService:
    """PatchApplyEvalService 测试。"""

    def test_run_all_passes(self, tmp_path):
        summary = PatchApplyEvalService.run_all(tmp_path)
        assert summary.total_cases >= 10
        assert summary.passed == summary.total_cases, (
            f"期望全部通过，实际 {summary.passed}/{summary.total_cases}。"
            f"失败案例: {[(r.case_id, r.actual_result) for r in summary.results if not r.passed]}"
        )
        assert summary.failed == 0

    def test_single_modify_success(self, tmp_path):
        case_dir = tmp_path / "modify_ok"
        case_dir.mkdir()
        case = PatchApplyEvalCase("modify_ok", "测试", True, "")
        result = PatchApplyEvalService._run(case, case_dir)
        assert result.passed is True
        assert "成功" in result.actual_result

    def test_agent_self_approve_blocked(self, tmp_path):
        case_dir = tmp_path / "test"
        case_dir.mkdir()
        case = PatchApplyEvalCase("agent_self", "测试", False, "自我批准")
        result = PatchApplyEvalService._run(case, case_dir)
        assert result.passed is True
        assert "失败" in result.actual_result

    def test_blocked_dotenv(self, tmp_path):
        case_dir = tmp_path / "test"
        case_dir.mkdir()
        case = PatchApplyEvalCase("block_env", "测试", False, "secret")
        result = PatchApplyEvalService._run(case, case_dir)
        assert result.passed is True

    def test_blocked_dotclaude(self, tmp_path):
        case_dir = tmp_path / "test"
        case_dir.mkdir()
        case = PatchApplyEvalCase("block_claude", "测试", False, "禁止写入目录")
        result = PatchApplyEvalService._run(case, case_dir)
        assert result.passed is True

    def test_stale_proposal_blocked(self, tmp_path):
        case_dir = tmp_path / "test"
        case_dir.mkdir()
        case = PatchApplyEvalCase("stale", "测试", False, "过期")
        result = PatchApplyEvalService._run(case, case_dir)
        assert result.passed is True

    def test_multi_file_no_cross_corruption(self, tmp_path):
        """多文件修改不能串改。"""
        case_dir = tmp_path / "multi"
        case_dir.mkdir()
        case = PatchApplyEvalCase("multi_ok", "测试", True, "")
        result = PatchApplyEvalService._run(case, case_dir)
        assert result.passed is True
        assert "独立修改" in result.safety_notes or result.files_changed == ["src/a.py", "src/b.py"]

    def test_diff_injection_blocked(self, tmp_path):
        case_dir = tmp_path / "test"
        case_dir.mkdir()
        case = PatchApplyEvalCase("inject", "测试", False, "非目标文件")
        result = PatchApplyEvalService._run(case, case_dir)
        assert result.passed is True

    def test_summary_to_dict(self, tmp_path):
        summary = PatchApplyEvalService.run_all(tmp_path)
        d = summary.to_dict()
        assert "total_cases" in d
        assert "passed" in d
        assert "all_passed" in d
        assert d["all_passed"] is True

    def test_result_to_dict(self):
        r = PatchApplyEvalResult(
            case_id="test", passed=True, expected_result="成功",
            actual_result="成功", files_changed=["a.py"],
            safety_notes="安全", rollback_hint="git checkout",
        )
        d = r.to_dict()
        assert d["case_id"] == "test"
        assert d["passed"] is True

    def test_case_to_dict(self):
        c = PatchApplyEvalCase("test", "测试案例", False, "拒绝")
        d = c.to_dict()
        assert d["case_id"] == "test"
        assert d["description"] == "测试案例"
