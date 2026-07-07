"""Unit tests for FailureClassifier. Classification only, no auto-fix."""
from bolt_core.failure_classifier import FailureClassifier


def test_categories_returns_all():
    """categories returns all 8 failure categories."""
    cats = FailureClassifier.categories()
    assert len(cats) == 8
    expected = {"user_input", "permission_waiting", "tool_failure",
                "test_failure", "network_failure", "code_quality",
                "security_block", "unknown"}
    assert set(cats.keys()) == expected


def test_classify_permission_denied():
    """permission denied -> security_block."""
    result = FailureClassifier.classify("permission denied: cannot execute")
    assert result["category"] == "security_block"
    assert result["retryable"] is False


def test_classify_network_timeout():
    """timeout -> network_failure."""
    result = FailureClassifier.classify("ConnectionError: timeout after 30s")
    assert result["category"] == "network_failure"
    assert result["retryable"] is True


def test_classify_test_assertion():
    """test assertion -> test_failure."""
    result = FailureClassifier.classify("AssertionError: expected True, got False")
    assert result["category"] == "test_failure"
    assert result["retryable"] is True


def test_classify_tool_error():
    """tool error -> tool_failure."""
    result = FailureClassifier.classify("ToolError: command failed with exit code 1")
    assert result["category"] == "tool_failure"
    assert result["retryable"] is True


def test_classify_validation_error():
    """validation error -> user_input."""
    result = FailureClassifier.classify("ValueError: missing required parameter")
    assert result["category"] == "user_input"
    assert result["retryable"] is True


def test_classify_waiting_permission():
    """waiting_permission -> permission_waiting."""
    result = FailureClassifier.classify("status: waiting_permission, needs approval")
    assert result["category"] == "permission_waiting"
    assert result["retryable"] is False


def test_classify_code_quality():
    """type error -> code_quality."""
    result = FailureClassifier.classify("TypeError: build failed during tsc check")
    assert result["category"] == "code_quality"


def test_classify_unknown():
    """unknown error -> unknown category."""
    result = FailureClassifier.classify("something inexplicable happened")
    assert result["category"] == "unknown"
    assert result["retryable"] is False


def test_classify_uses_context():
    """Context is used for classification."""
    result = FailureClassifier.classify("error occurred", context="network timeout during deployment")
    assert result["category"] == "network_failure"


def test_is_retryable():
    """is_retryable returns correct boolean."""
    assert FailureClassifier.is_retryable("timeout") is True
    assert FailureClassifier.is_retryable("permission denied") is False
    assert FailureClassifier.is_retryable("???") is False  # unknown


def test_all_suggestions_are_chinese():
    """All category suggestions contain Chinese characters."""
    cats = FailureClassifier.categories()
    for code, meta in cats.items():
        assert any('\u4e00' <= c <= '\u9fff' for c in meta["label"]), f"{code} label not Chinese"
        assert any('\u4e00' <= c <= '\u9fff' for c in meta["suggestion"]), f"{code} suggestion not Chinese"


def test_classify_result_has_all_fields():
    """classify result includes all required fields."""
    result = FailureClassifier.classify("timeout error")
    assert "category" in result
    assert "label" in result
    assert "suggestion" in result
    assert "retryable" in result
    assert "auto_fix_possible" in result
    assert "error_summary" in result


def test_no_auto_fix():
    """All categories have auto_fix_possible = False."""
    cats = FailureClassifier.categories()
    for code, meta in cats.items():
        assert meta["auto_fix_possible"] is False, f"{code} should not auto-fix"
