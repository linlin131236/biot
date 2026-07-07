"""Tests for E2ETaskDogfoodService (M118)."""
import pytest
from bolt_core.e2e_task_dogfood import E2ETaskDogfoodService


class TestE2EDogfood:
    def test_run_all_passes(self, tmp_path):
        summary = E2ETaskDogfoodService.run_all(tmp_path)
        assert summary.total_scenarios == 4
        assert summary.passed == summary.total_scenarios, (
            f"失败: {[(r.scenario, r.steps) for r in summary.results if not r.passed]}")

    def test_happy_path(self, tmp_path):
        d = tmp_path / "happy"; d.mkdir()
        result = E2ETaskDogfoodService._happy_path(d)
        assert result.passed is True, f"happy path失败: {result.steps}"
        assert result.audit_complete is True
        assert result.triggered_dangerous_ops is False

    def test_no_approval_blocked(self, tmp_path):
        d = tmp_path / "noapp"; d.mkdir()
        result = E2ETaskDogfoodService._no_approval(d)
        assert result.passed is True, f"no_approval失败: {result.steps}"

    def test_stale_blocked(self, tmp_path):
        d = tmp_path / "stale"; d.mkdir()
        result = E2ETaskDogfoodService._stale_path(d)
        assert result.passed is True, f"stale失败: {result.steps}"

    def test_audit_chain_complete(self, tmp_path):
        d = tmp_path / "create"; d.mkdir()
        result = E2ETaskDogfoodService._create_and_audit(d)
        assert result.passed is True
        assert result.audit_complete is True

    def test_no_dangerous_ops(self, tmp_path):
        summary = E2ETaskDogfoodService.run_all(tmp_path)
        for r in summary.results:
            assert r.triggered_dangerous_ops is False, f"{r.scenario} 触发了危险操作"

    def test_summary_to_dict(self, tmp_path):
        summary = E2ETaskDogfoodService.run_all(tmp_path)
        d = summary.to_dict()
        assert d["all_passed"] is True
