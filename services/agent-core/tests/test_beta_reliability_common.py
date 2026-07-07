"""Tests for shared beta reliability review result models."""
from bolt_core.beta_reliability_common import BetaCheck, BetaReviewResult


def test_beta_review_result_counts_passes_and_failures():
    result = BetaReviewResult(
        checks=[
            BetaCheck(name="文档链完整", passed=True, detail="ok"),
            BetaCheck(name="安全门禁", passed=False, detail="missing", severity="blocking"),
        ],
        warnings=["需要人工复审"],
        next_step="等待爸爸复审",
    )

    data = result.to_dict()

    assert data["total"] == 2
    assert data["passed_count"] == 1
    assert data["failed_count"] == 1
    assert data["all_passed"] is False
    assert data["p1_failures"] == ["安全门禁"]
    assert data["warnings"] == ["需要人工复审"]
    assert data["next_step"] == "等待爸爸复审"


def test_beta_review_result_can_record_all_passed_state():
    result = BetaReviewResult(
        checks=[BetaCheck(name="只读检查", passed=True, detail="没有副作用")],
        next_step="可以进入下一项人工复审",
    )

    data = result.to_dict()

    assert data["all_passed"] is True
    assert data["p1_failures"] == []
    assert data["checks"][0]["severity"] == "info"
