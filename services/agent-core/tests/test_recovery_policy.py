"""Unit tests for RecoveryPolicyService. Read-only only."""
from bolt_core.recovery_policy import RecoveryPolicyService


def test_list_scenarios_returns_dict():
    """list_scenarios returns dict with scenarios, categories, total, disclaimer."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    assert "scenarios" in result
    assert "categories" in result
    assert "total" in result
    assert "disclaimer" in result


def test_scenarios_have_required_fields():
    """Each scenario has all required fields."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    required = {"code", "title", "category", "severity", "severity_label",
                "description", "recovery_steps", "auto_recovery_possible",
                "auto_recovery_label", "warnings"}
    for s in result["scenarios"]:
        missing = required - set(s.keys())
        assert not missing, f"scenario {s.get('code', '?')} missing: {missing}"
        assert isinstance(s["recovery_steps"], list)
        assert isinstance(s["warnings"], list)


def test_has_audit_scenarios():
    """Recovery policy includes audit corruption scenarios."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    codes = {s["code"] for s in result["scenarios"]}
    assert "audit_corrupt" in codes
    assert "audit_missing" in codes


def test_has_release_scenarios():
    """Recovery policy includes release failure scenarios."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    codes = {s["code"] for s in result["scenarios"]}
    assert "release_push_rejected" in codes
    assert "release_tag_conflict" in codes


def test_has_permission_scenarios():
    """Recovery policy includes permission mishandling scenarios."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    codes = {s["code"] for s in result["scenarios"]}
    assert "perm_misapproval" in codes
    assert "perm_gate_bypass" in codes


def test_has_interruption_scenarios():
    """Recovery policy includes task interruption scenarios."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    codes = {s["code"] for s in result["scenarios"]}
    assert "task_interrupted" in codes
    assert "process_crash" in codes


def test_no_auto_execution():
    """All scenarios state whether auto recovery is possible, and warnings are present."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    for s in result["scenarios"]:
        assert isinstance(s["auto_recovery_possible"], bool)
        assert isinstance(s["auto_recovery_label"], str)
        assert len(s["warnings"]) > 0 or s["auto_recovery_possible"]


def test_categories_group_scenarios():
    """Categories dict groups scenarios by category."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    total_in_cats = sum(len(v) for v in result["categories"].values())
    assert total_in_cats == result["total"]
    assert total_in_cats == len(result["scenarios"])


def test_chinese_labels():
    """Scenario titles and severity labels are in Chinese."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    for s in result["scenarios"]:
        # All titles should contain Chinese characters
        assert any('\u4e00' <= c <= '\u9fff' for c in s["title"])
        assert any('\u4e00' <= c <= '\u9fff' for c in s["severity_label"])


def test_disclaimer_mentions_readonly():
    """Disclaimer states read-only nature."""
    svc = RecoveryPolicyService()
    result = svc.list_scenarios()
    assert "只读" in result["disclaimer"] or "不自动" in result["disclaimer"]


def test_is_read_only():
    """Multiple calls return identical results."""
    svc = RecoveryPolicyService()
    r1 = svc.list_scenarios()
    r2 = svc.list_scenarios()
    assert r1 == r2
