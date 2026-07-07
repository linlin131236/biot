"""Tests for ReviewerIndependentGateService."""
from bolt_core.reviewer_independent_gate import ReviewerIndependentGateService


def test_evaluate_approved():
    svc = ReviewerIndependentGateService()
    result = svc.evaluate(
        workflow_id="wf-1",
        builder_context="ctx-builder",
        reviewer_context="ctx-reviewer",
        builder_output_summary="实现登录",
        code_changes="added auth.py",
        tests_status="passed",
        evidence_refs=["test.log"],
        source_refs=["docs/spec.md"],
    )
    assert result.verdict == "approved"
    assert result.is_self_approval is False


def test_evaluate_self_approval_blocked():
    svc = ReviewerIndependentGateService()
    result = svc.evaluate(
        workflow_id="wf-1",
        builder_context="ctx-same",
        reviewer_context="ctx-same",  # same!
        builder_output_summary="x",
        code_changes="x",
        tests_status="x",
        evidence_refs=["e"],
        source_refs=["s"],
    )
    assert result.verdict == "blocked"
    assert result.is_self_approval is True


def test_evaluate_no_evidence_blocked():
    svc = ReviewerIndependentGateService()
    result = svc.evaluate(
        workflow_id="wf-1",
        builder_context="ctx-b",
        reviewer_context="ctx-r",
        builder_output_summary="x",
        code_changes="x",
        tests_status="x",
        evidence_refs=[],
        source_refs=[],
    )
    assert result.verdict == "blocked"


def test_evaluate_p1_blocked():
    svc = ReviewerIndependentGateService()
    result = svc.evaluate(
        workflow_id="wf-1",
        builder_context="ctx-b",
        reviewer_context="ctx-r",
        builder_output_summary="x",
        code_changes="x",
        tests_status="failed",
        evidence_refs=["e"],
        source_refs=["s"],
        findings=[{"severity": "P1", "desc": "安全漏洞"}],
    )
    assert result.verdict == "blocked"


def test_evaluate_p2_changes_requested():
    svc = ReviewerIndependentGateService()
    result = svc.evaluate(
        workflow_id="wf-1",
        builder_context="ctx-b",
        reviewer_context="ctx-r",
        builder_output_summary="x",
        code_changes="x",
        tests_status="passed",
        evidence_refs=["e"],
        source_refs=["s"],
        findings=[{"severity": "P2", "desc": "代码风格"}],
    )
    assert result.verdict == "changes_requested"


def test_evaluate_no_tests_warning():
    svc = ReviewerIndependentGateService()
    result = svc.evaluate(
        workflow_id="wf-1",
        builder_context="ctx-b",
        reviewer_context="ctx-r",
        builder_output_summary="x",
        code_changes="x",
        tests_status="",  # missing
        evidence_refs=["e"],
        source_refs=["s"],
    )
    assert result.verdict == "changes_requested"


def test_list_results():
    svc = ReviewerIndependentGateService()
    svc.evaluate("wf", "cb", "cr", "s", "c", "t", ["e"], ["s"])
    assert len(svc.list_results()) == 1


def test_get_result_not_found():
    svc = ReviewerIndependentGateService()
    assert svc.get_result("nonexistent") is None
