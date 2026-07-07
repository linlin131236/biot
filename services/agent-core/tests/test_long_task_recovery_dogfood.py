"""Unit tests for LongTaskRecoveryDogfoodService. Readiness checks, safety."""
import pytest

from bolt_core.long_task_recovery_dogfood import (
    LongTaskRecoveryDogfoodService,
    DogfoodReport,
    DogfoodCheck,
)


def test_assess_returns_report():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    assert isinstance(report, DogfoodReport)
    assert report.report_id.startswith("dogfood_")
    assert report.timestamp > 0


def test_assess_has_nine_checks():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    assert len(report.checks) == 9, f"expected 9 checks, got {len(report.checks)}"


def test_assess_each_check_has_required_fields():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    required = ["check_id", "label_cn", "passed", "severity", "detail", "source"]
    for check in report.checks:
        for key in required:
            assert key in check, f"check missing field: {key}"


def test_assess_all_checks_have_chinese_labels():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    for check in report.checks:
        label = check["label_cn"]
        assert any('\u4e00' <= c <= '\u9fff' for c in label), \
            f"label_cn has no Chinese: {label}"


def test_assess_summary_is_chinese():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    assert any('\u4e00' <= c <= '\u9fff' for c in report.summary)


def test_assess_readiness_is_valid():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    assert report.readiness in ("ready", "not_ready", "needs_review")


def test_assess_to_dict():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    d = report.to_dict()
    keys = ["report_id", "timestamp", "overall_passed", "checks",
            "summary", "blockers", "warnings", "readiness"]
    for key in keys:
        assert key in d, f"missing: {key}"


def test_task_graph_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_task_graph()
    assert "check_id" in result
    assert result["check_id"] == "task_graph"


def test_state_machine_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_state_machine()
    assert result["check_id"] == "state_machine"


def test_pause_resume_permissions_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_pause_resume_permissions()
    assert result["check_id"] == "pause_resume_perms"
    # Should pass: M66 enforces permission re-verification
    assert result["passed"] is True


def test_steering_safety_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_steering_safety()
    assert result["check_id"] == "steering_safety"
    # Should pass: M67 abort/change_goal go to pending only
    assert result["passed"] is True


def test_budget_blocks_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_budget_blocks()
    assert result["check_id"] == "budget_blocks"
    # Should pass: M68 blocks when steps exceeded
    assert result["passed"] is True


def test_failure_classifier_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_failure_classifier_chinese()
    assert result["check_id"] == "failure_classifier_cn"


def test_retry_loop_safety_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_retry_loop_safety()
    assert result["check_id"] == "retry_loop_safety"
    # Should pass: dangerous tools are properly classified
    assert result["passed"] is True


def test_permission_gate_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_permission_gate()
    assert result["check_id"] == "permission_gate"
    # PermissionGate should deny dangerous shell commands
    assert result["passed"] is True


def test_traceability_check_runs():
    svc = LongTaskRecoveryDogfoodService()
    result = svc._check_traceability()
    assert result["check_id"] == "traceability"


# ── Safety invariants ─────────────────────────────────────────────────

def test_service_has_no_execute_method():
    """Dogfood service must not have any execute/run/apply methods."""
    svc = LongTaskRecoveryDogfoodService()
    assert not hasattr(svc, "execute")
    assert not hasattr(svc, "run")
    assert not hasattr(svc, "apply")


def test_service_has_no_approve_method():
    svc = LongTaskRecoveryDogfoodService()
    assert not hasattr(svc, "approve_permission")
    assert not hasattr(svc, "approve")


def test_happy_path_report():
    """Full assessment should pass or have clear reasons for failures."""
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    # The report should have a valid readiness status
    assert report.readiness in ("ready", "not_ready", "needs_review")
    # If not ready, must have blockers or warnings explaining why
    if report.readiness != "ready":
        assert len(report.blockers) > 0 or len(report.warnings) > 0, \
            "non-ready report must explain why"


def test_blockers_have_chinese_labels():
    svc = LongTaskRecoveryDogfoodService()
    report = svc.assess()
    for blocker in report.blockers:
        assert any('\u4e00' <= c <= '\u9fff' for c in blocker), \
            f"blocker has no Chinese: {blocker}"
