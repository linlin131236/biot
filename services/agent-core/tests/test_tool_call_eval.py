"""Tests for ToolCallEvalService (M111)."""
import pytest

from bolt_core.tool_call_eval import (
    EvalCase,
    EvalResult,
    EvalSummary,
    ToolCallEvalService,
    _build_eval_cases,
    _build_eval_registry,
)
from bolt_core.tool_registry import (
    CATEGORY_DANGEROUS,
    CATEGORY_READ_ONLY,
    CATEGORY_SIDE_EFFECT,
    CATEGORY_WRITE,
)


class TestEvalCases:
    """评估案例定义测试。"""

    def test_at_least_12_cases(self):
        cases = _build_eval_cases()
        assert len(cases) >= 12, f"需要至少12个eval cases，当前只有{len(cases)}个"

    def test_all_cases_have_unique_ids(self):
        cases = _build_eval_cases()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids)), "eval case ID必须唯一"

    def test_all_cases_have_chinese_explanation(self):
        cases = _build_eval_cases()
        for c in cases:
            assert c.chinese_explanation, f"case {c.case_id} 缺少中文说明"
            # Check contains Chinese characters
            has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in c.chinese_explanation)
            assert has_chinese, f"case {c.case_id} 的说明不是中文"

    def test_dangerous_cases_exist(self):
        cases = _build_eval_cases()
        dangerous_cases = [c for c in cases if c.expected_category == CATEGORY_DANGEROUS]
        assert len(dangerous_cases) >= 4, f"需要至少4个dangerous案例，当前{len(dangerous_cases)}个"


class TestEvalRegistry:
    """评估注册表测试。"""

    def test_registry_has_all_categories(self):
        registry = _build_eval_registry()
        categories = {t.category for t in registry.list()}
        assert CATEGORY_READ_ONLY in categories
        assert CATEGORY_WRITE in categories
        assert CATEGORY_DANGEROUS in categories

    def test_registry_has_min_tools(self):
        registry = _build_eval_registry()
        assert len(registry) >= 8


class TestToolCallEvalService:
    """ToolCallEvalService 测试。"""

    def test_list_cases(self):
        service = ToolCallEvalService()
        cases = service.list_cases()
        assert len(cases) >= 12

    def test_get_case_exists(self):
        service = ToolCallEvalService()
        case = service.get_case("read_normal_file")
        assert case is not None
        assert case["case_id"] == "read_normal_file"

    def test_get_case_not_exists(self):
        service = ToolCallEvalService()
        case = service.get_case("nonexistent")
        assert case is None

    def test_run_single_read_file(self):
        service = ToolCallEvalService()
        result = service.run_single("read_normal_file")
        assert result is not None
        assert result.overall_passed is True
        assert result.selected_tool_correct is True

    def test_run_single_not_exists(self):
        service = ToolCallEvalService()
        result = service.run_single("nonexistent")
        assert result is None

    def test_run_all_passes(self):
        service = ToolCallEvalService()
        summary = service.run_all()
        assert summary.total_cases >= 12
        assert summary.passed == summary.total_cases, (
            f"期望全部通过，实际 {summary.passed}/{summary.total_cases}。"
            f"失败案例: {[r.case_id for r in summary.results if not r.overall_passed]}"
        )
        assert summary.failed == 0

    def test_dangerous_all_blocked(self):
        """所有dangerous类别的案例必须全部blocked。"""
        service = ToolCallEvalService()
        summary = service.run_all()
        cases = _build_eval_cases()
        dangerous_ids = {c.case_id for c in cases if c.expected_category == CATEGORY_DANGEROUS}
        for r in summary.results:
            if r.case_id in dangerous_ids:
                assert r.dangerous_blocked is True, f"dangerous case {r.case_id} 未被正确阻断"
                assert r.overall_passed is True, f"dangerous case {r.case_id} 应通过（dangerous被阻断即通过）"

    def test_unknown_tool_blocked(self):
        """未知工具必须被阻断。"""
        service = ToolCallEvalService()
        result = service.run_single("reject_unknown_tool")
        assert result is not None
        assert result.overall_passed is True
        # The unknown tool should not be in the registry
        assert result.dangerous_blocked is True

    def test_read_only_no_approval(self):
        """只读操作不应要求人工批准。"""
        service = ToolCallEvalService()
        result = service.run_single("read_normal_file")
        assert result is not None
        assert result.overall_passed is True

    def test_summary_to_dict(self):
        service = ToolCallEvalService()
        summary = service.run_all()
        d = summary.to_dict()
        assert "total_cases" in d
        assert "passed" in d
        assert "failed" in d
        assert "all_passed" in d
        assert d["all_passed"] is True

    def test_eval_result_to_dict(self):
        result = EvalResult(
            case_id="test",
            selected_tool_correct=True,
            permission_correct=True,
            dangerous_blocked=True,
            explanation_zh="测试通过",
            overall_passed=True,
        )
        d = result.to_dict()
        assert d["case_id"] == "test"
        assert d["overall_passed"] is True

    def test_eval_case_to_dict(self):
        case = EvalCase(
            case_id="test",
            user_intent="测试意图",
            expected_category=CATEGORY_READ_ONLY,
            allowed_tools=["read_file"],
            forbidden_tools=["delete_file"],
            expected_permission="read",
            chinese_explanation="这是测试案例",
        )
        d = case.to_dict()
        assert d["case_id"] == "test"
        assert d["user_intent"] == "测试意图"
