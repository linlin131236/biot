"""Tests for MultiAgentCollaborationEvalService (M115)."""
import pytest
from bolt_core.multi_agent_collaboration_eval import MultiAgentCollaborationEvalService


class TestMultiAgentEval:
    def test_at_least_10_cases(self):
        cases = MultiAgentCollaborationEvalService._cases()
        assert len(cases) >= 10, f"需要≥10，当前{len(cases)}"

    def test_run_all_passes(self):
        summary = MultiAgentCollaborationEvalService.run_all()
        assert summary.total_cases >= 10
        assert summary.passed == summary.total_cases, (
            f"失败: {[(r.case_id, r.actual_boundary) for r in summary.results if not r.passed]}")

    def test_self_approval_blocked(self):
        summary = MultiAgentCollaborationEvalService.run_all()
        builder = [r for r in summary.results if r.case_id == "builder_no_self_approve"][0]
        assert builder.passed is True

    def test_reviewer_independent(self):
        summary = MultiAgentCollaborationEvalService.run_all()
        reviewer = [r for r in summary.results if r.case_id == "reviewer_independent"][0]
        assert reviewer.passed is True

    def test_skilllearner_needs_approval(self):
        summary = MultiAgentCollaborationEvalService.run_all()
        sl = [r for r in summary.results if "skilllearner" in r.case_id]
        for r in sl:
            assert r.passed is True

    def test_summary_to_dict(self):
        summary = MultiAgentCollaborationEvalService.run_all()
        d = summary.to_dict()
        assert d["all_passed"] is True
