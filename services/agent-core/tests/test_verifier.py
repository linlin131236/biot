from bolt_core.tool_protocol import ToolResult
from bolt_core.verifier import Verifier


def test_verifier_maps_executed_to_complete():
    result = Verifier().verify(ToolResult.executed("tool_1", "done"))

    assert result.status == "complete"
    assert result.reason == "executed"


def test_verifier_maps_pending_to_pause():
    result = Verifier().verify(ToolResult.pending("tool_1", "needs approval"))

    assert result.status == "pause_for_permission"


def test_verifier_maps_denied_and_rejected_to_terminal_failure():
    denied = Verifier().verify(ToolResult.denied("tool_1", "blocked"))
    rejected = Verifier().verify(ToolResult.rejected("tool_2", "no"))

    assert denied.status == "terminal_failure"
    assert rejected.status == "terminal_failure"


def test_verifier_maps_failed_to_recoverable_failure():
    result = Verifier().verify(ToolResult.failed("tool_1", "read failed"))

    assert result.status == "recoverable_failure"


def test_verifier_requests_replan_for_missing_or_unknown_result():
    missing = Verifier().verify(None)
    unknown = Verifier().verify(ToolResult("tool_1", "strange", "odd"))

    assert missing.status == "needs_replan"
    assert unknown.status == "needs_replan"
