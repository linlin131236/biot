"""Tests for MemoryRetrievalEvalService (M116)."""
import pytest
from bolt_core.memory_retrieval_eval import MemoryRetrievalEvalService


class TestMemoryRetrievalEval:
    def test_at_least_10_cases(self):
        cases = MemoryRetrievalEvalService._cases()
        assert len(cases) >= 10, f"需要≥10，当前{len(cases)}"

    def test_run_all_passes(self):
        summary = MemoryRetrievalEvalService.run_all()
        assert summary.total_cases >= 10
        assert summary.passed == summary.total_cases, (
            f"失败: {[(r.case_id, r.details) for r in summary.results if not r.passed]}")

    def test_secret_case_safe(self):
        summary = MemoryRetrievalEvalService.run_all()
        secret = [r for r in summary.results if r.case_id == "secret_query_blocked"][0]
        assert secret.safety is True

    def test_all_have_source(self):
        summary = MemoryRetrievalEvalService.run_all()
        for r in summary.results:
            assert r.source_traceability is True, f"{r.case_id} 缺少source"

    def test_irrelevant_not_passed(self):
        summary = MemoryRetrievalEvalService.run_all()
        irr = [r for r in summary.results if r.case_id == "irrelevant_query_fails"][0]
        assert irr.passed is True
        assert irr.relevance == 0.0

    def test_summary_to_dict(self):
        summary = MemoryRetrievalEvalService.run_all()
        d = summary.to_dict()
        assert d["all_passed"] is True
