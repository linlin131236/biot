"""Unit tests for SafeRetryLoop. Validates retry conditions, never auto-executes."""
from bolt_core.safe_retry_loop import SafeRetryLoop, SafeRetryPolicy


def test_assess_retryable_failure_allowed():
    """Retryable failure categories like network_failure are allowed."""
    decision = SafeRetryPolicy.assess("network_failure", attempt=0, max_attempts=3)
    assert decision["allowed"] is True


def test_assess_security_block_denied():
    """security_block is never retryable."""
    decision = SafeRetryPolicy.assess("security_block", attempt=0, max_attempts=3)
    assert decision["allowed"] is False


def test_assess_permission_waiting_denied():
    """permission_waiting is never retryable."""
    decision = SafeRetryPolicy.assess("permission_waiting", attempt=0, max_attempts=3)
    assert decision["allowed"] is False


def test_assess_max_attempts_exceeded():
    """Exceeding max_attempts denies retry."""
    decision = SafeRetryPolicy.assess("network_failure", attempt=3, max_attempts=3)
    assert decision["allowed"] is False


def test_assess_dangerous_tool_denied():
    """Dangerous tools cannot be auto-retried."""
    decision = SafeRetryPolicy.assess("tool_failure", tool_names=["git_push"], attempt=0, max_attempts=3)
    assert decision["allowed"] is False


def test_assess_side_effect_tool_allowed():
    """Side-effect tools are allowed for retry (not dangerous)."""
    decision = SafeRetryPolicy.assess("tool_failure", tool_names=["write_file"], attempt=0, max_attempts=3)
    assert decision["allowed"] is True


def test_assess_unknown_failure_denied():
    """Unknown failure category denies retry."""
    decision = SafeRetryPolicy.assess("unknown", attempt=0, max_attempts=3)
    assert decision["allowed"] is False


def test_loop_tracks_attempts():
    """SafeRetryLoop correctly tracks attempts."""
    loop = SafeRetryLoop(max_attempts=3)
    assert loop.attempts == 0
    assert loop.exhausted is False
    loop.record_retry("network_failure", error_text="timeout")
    assert loop.attempts == 1
    loop.record_retry("network_failure", error_text="timeout again")
    assert loop.attempts == 2


def test_loop_exhausted():
    """Loop is exhausted after max_attempts."""
    loop = SafeRetryLoop(max_attempts=2)
    loop.record_retry("network_failure")
    loop.record_retry("network_failure")
    assert loop.exhausted is True
    assert loop.can_retry("network_failure") is False


def test_loop_can_retry_respects_category():
    """can_retry returns False for never-retry categories."""
    loop = SafeRetryLoop(max_attempts=3)
    assert loop.can_retry("security_block") is False
    assert loop.can_retry("network_failure") is True


def test_loop_record_retry_returns_decision():
    """record_retry returns a full decision dict with history."""
    loop = SafeRetryLoop(max_attempts=3)
    d = loop.record_retry("network_failure", error_text="timeout")
    assert d["allowed"] is True
    assert "history" in d
    assert len(d["history"]) == 1


def test_loop_record_blocked_retry_not_allowed():
    """Recording a blocked retry returns allowed=False."""
    loop = SafeRetryLoop(max_attempts=3)
    d = loop.record_retry("security_block", error_text="permission denied")
    assert d["allowed"] is False


def test_summary_includes_disclaimer():
    """Loop summary includes disclaimer about PermissionGate."""
    loop = SafeRetryLoop(max_attempts=3)
    s = loop.summary()
    assert "disclaimer" in s
    assert "PermissionGate" in s["disclaimer"] or "人工" in s["disclaimer"]


def test_no_auto_execution():
    """SafeRetryLoop has no execute/run/approve methods."""
    loop = SafeRetryLoop()
    methods = [m for m in dir(loop) if not m.startswith("_") and callable(getattr(loop, m))]
    for m in methods:
        assert "execute" not in m.lower()
