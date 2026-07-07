"""Tests for PermissionBoundaryEvalService (M114)."""
import pytest

from bolt_core.permission_boundary_eval import (
    PermissionBoundaryEvalService,
    PermBoundaryEvalCase,
)


class TestPermBoundaryEval:
    def test_at_least_12_cases(self):
        cases = PermissionBoundaryEvalService._cases()
        assert len(cases) >= 12, f"需要≥12，当前{len(cases)}"

    def test_run_all_passes(self):
        service = PermissionBoundaryEvalService()
        summary = service.run_all()
        assert summary.total_cases >= 12
        assert summary.passed == summary.total_cases, (
            f"期望全通过，实际{summary.passed}/{summary.total_cases}。"
            f"失败: {[(r.case_id, r.actual_decision) for r in summary.results if not r.passed]}"
        )

    def test_dangerous_all_blocked(self):
        service = PermissionBoundaryEvalService()
        summary = service.run_all()
        dangerous_cases = {"dangerous_always_blocked_push", "dangerous_always_blocked_release",
                           "dangerous_always_blocked_tag", "dangerous_always_blocked_delete",
                           "secret_read_blocked"}
        for r in summary.results:
            if r.case_id in dangerous_cases:
                assert r.actual_decision != "allowed", f"{r.case_id} 应被阻断但被允许"

    def test_read_allowed(self):
        service = PermissionBoundaryEvalService()
        summary = service.run_all()
        read_result = [r for r in summary.results if r.case_id == "read_allowed"][0]
        assert read_result.actual_decision == "allowed"

    def test_unknown_tool_blocked(self):
        service = PermissionBoundaryEvalService()
        summary = service.run_all()
        unknown = [r for r in summary.results if r.case_id == "unknown_tool_blocked"][0]
        assert unknown.actual_decision == "denied"

    def test_summary_to_dict(self):
        service = PermissionBoundaryEvalService()
        summary = service.run_all()
        d = summary.to_dict()
        assert d["all_passed"] is True

    def test_case_to_dict(self):
        c = PermBoundaryEvalCase("test", "desc", "tool", "", "allowed", "")
        d = c.to_dict()
        assert d["case_id"] == "test"
