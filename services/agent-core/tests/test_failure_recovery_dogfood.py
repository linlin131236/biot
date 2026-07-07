"""Tests for FailureRecoveryDogfoodService (M119)."""
import pytest
from bolt_core.failure_recovery_dogfood import FailureRecoveryDogfoodService


class TestFailureRecoveryDogfood:
    def test_at_least_6_cases(self):
        summary = FailureRecoveryDogfoodService.run_all()
        assert summary.total_cases >= 6, f"需要≥6，当前{summary.total_cases}"

    def test_run_all_passes(self):
        summary = FailureRecoveryDogfoodService.run_all()
        assert summary.passed == summary.total_cases, (
            f"失败: {[(r.case_id, r.recovery_plan) for r in summary.results if not r.passed]}")

    def test_auto_fix_always_false(self):
        summary = FailureRecoveryDogfoodService.run_all()
        for r in summary.results:
            assert r.auto_fix_allowed is False, f"{r.case_id} auto_fix应为False"

    def test_dangerous_retry_blocked(self):
        summary = FailureRecoveryDogfoodService.run_all()
        dangerous = {"permission_denied", "stale_proposal", "interrupted_long_task"}
        for r in summary.results:
            if r.case_id in dangerous:
                assert r.safe_to_retry is False, f"{r.case_id} 不应允许重试"

    def test_all_chinese_plans(self):
        summary = FailureRecoveryDogfoodService.run_all()
        for r in summary.results:
            has_cn = any('\u4e00' <= c <= '\u9fff' for c in r.recovery_plan)
            assert has_cn, f"{r.case_id} 恢复计划应包含中文"

    def test_summary_to_dict(self):
        summary = FailureRecoveryDogfoodService.run_all()
        d = summary.to_dict()
        assert d["all_passed"] is True
