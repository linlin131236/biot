"""Tests for MultiAgentRecoveryService."""
from bolt_core.multi_agent_recovery import MultiAgentRecoveryService, RecoveryScenario


def test_classify_builder_test_failure():
    svc = MultiAgentRecoveryService()
    plan = svc.classify_and_suggest("builder_test_failure", "3 tests failed", ["test.log"])
    assert plan.scenario == RecoveryScenario.BUILDER_TEST_FAILURE
    assert plan.responsible_role == "builder"
    assert len(plan.recovery_steps_cn) >= 3


def test_classify_reviewer_blocked():
    svc = MultiAgentRecoveryService()
    plan = svc.classify_and_suggest("reviewer_blocked", "P1 issue found", ["review.md"])
    assert plan.requires_human_confirmation is True
    assert "不允许继续到 approved" in " ".join(plan.recovery_steps_cn).lower() or "approved" in " ".join(plan.recovery_steps_cn).lower()


def test_classify_permission_waiting():
    svc = MultiAgentRecoveryService()
    plan = svc.classify_and_suggest("permission_waiting", "awaiting approval")
    assert plan.scenario == RecoveryScenario.PERMISSION_WAITING
    assert "不自动批准" in " ".join(plan.recovery_steps_cn)


def test_classify_stale_context():
    svc = MultiAgentRecoveryService()
    plan = svc.classify_and_suggest("stale_context", "context expired")
    assert plan.scenario == RecoveryScenario.STALE_CONTEXT
    assert "上下文" in " ".join(plan.recovery_steps_cn) or "M76" in " ".join(plan.recovery_steps_cn)


def test_classify_unknown():
    svc = MultiAgentRecoveryService()
    plan = svc.classify_and_suggest("unknown_failure", "mysterious error")
    assert plan.risk_level == "high"


def test_list_plans():
    svc = MultiAgentRecoveryService()
    svc.classify_and_suggest("builder_test_failure", "d")
    svc.classify_and_suggest("reviewer_blocked", "d")
    assert len(svc.list_plans()) == 2


def test_scenario_options():
    svc = MultiAgentRecoveryService()
    options = svc.scenario_options()
    assert len(options) == 8
    assert any(o["scenario"] == "planner_bad_scope" for o in options)


def test_all_scenarios_have_steps():
    svc = MultiAgentRecoveryService()
    for s in RecoveryScenario:
        plan = svc.classify_and_suggest(s.value, "test")
        assert len(plan.recovery_steps_cn) > 0, f"{s.value} has no recovery steps"
