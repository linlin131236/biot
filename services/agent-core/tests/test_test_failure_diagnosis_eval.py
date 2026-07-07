"""Tests for FailureDiagnosisEvalService (M113)."""
import pytest

from bolt_core.test_failure_diagnosis_eval import (
    FailureDiagnosis,
    FailureDiagnosisEvalCase,
    FailureDiagnosisEvalResult,
    FailureDiagnosisEvalService,
)


class TestFailureDiagnosisEval:
    """评估案例定义测试。"""

    def test_at_least_8_cases(self):
        cases = FailureDiagnosisEvalService._cases()
        assert len(cases) >= 8, f"需要至少8个failure cases，当前{len(cases)}个"

    def test_all_cases_have_unique_ids(self):
        cases = FailureDiagnosisEvalService._cases()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))


class TestFailureDiagnosisService:
    """诊断服务测试。"""

    def test_run_all_passes(self):
        summary = FailureDiagnosisEvalService.run_all()
        assert summary.total_cases >= 8
        assert summary.passed == summary.total_cases, (
            f"期望全部通过，实际 {summary.passed}/{summary.total_cases}。"
            f"失败: {[(r.case_id, r.notes) for r in summary.results if not r.passed]}"
        )

    def test_assertion_diagnosis(self):
        diag = FailureDiagnosisEvalService._diagnose(
            "FAILED test_app.py::test_add - assert 3 == 4"
        )
        assert diag.failure_category == "测试失败"
        assert "断言" in diag.likely_cause

    def test_secret_redaction(self):
        diag = FailureDiagnosisEvalService._diagnose(
            "Error: API key sk-proj-abc123def456ghi789jkl is invalid"
        )
        assert diag.is_auto_fix_allowed is False
        assert "sk-proj" not in diag.redacted_output
        assert "REDACTED" in diag.redacted_output

    def test_secret_leak_category(self):
        diag = FailureDiagnosisEvalService._diagnose(
            "Log: Bearer eyJhbGciOiJIUzI1NiJ9.secret.token used for auth"
        )
        assert diag.failure_category == "安全阻断"
        assert diag.is_auto_fix_allowed is False

    def test_auto_fix_always_false(self):
        """所有诊断必须 is_auto_fix_allowed=False。"""
        summary = FailureDiagnosisEvalService.run_all()
        for r in summary.results:
            assert r.diagnosis["is_auto_fix_allowed"] is False, (
                f"case {r.case_id} 的 auto_fix 应为 False"
            )

    def test_all_chinese_diagnosis(self):
        """所有诊断建议必须中文。"""
        summary = FailureDiagnosisEvalService.run_all()
        for r in summary.results:
            d = r.diagnosis
            for field in ("likely_cause", "recommended_next_step", "failure_category"):
                has_cn = any('\u4e00' <= c <= '\u9fff' for c in d.get(field, ""))
                assert has_cn, f"case {r.case_id} 的 {field} 应包含中文"

    def test_confidence_in_range(self):
        summary = FailureDiagnosisEvalService.run_all()
        for r in summary.results:
            conf = r.diagnosis.get("confidence", 0)
            assert 0 <= conf <= 1.0, f"confidence 应在 0-1，当前 {conf}"

    def test_diagnosis_to_dict(self):
        d = FailureDiagnosis(
            failure_category="测试失败", likely_cause="断言失败",
            recommended_next_step="检查", redacted_output="safe",
            confidence=0.9, is_auto_fix_allowed=False,
        )
        dd = d.to_dict()
        assert dd["is_auto_fix_allowed"] is False
        assert dd["failure_category"] == "测试失败"

    def test_result_to_dict(self):
        r = FailureDiagnosisEvalResult(
            case_id="test", passed=True, expected_category="测试失败",
            actual_category="测试失败", diagnosis={"key": "val"},
        )
        d = r.to_dict()
        assert d["passed"] is True

    def test_case_to_dict(self):
        c = FailureDiagnosisEvalCase("test", "desc", "raw", "cat", "kw")
        d = c.to_dict()
        assert d["case_id"] == "test"
