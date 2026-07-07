"""Unit tests for HumanSteeringService. Classification, safety, evidence."""
import pytest

from bolt_core.human_steering import (
    HumanSteeringService,
    SteeringIntent,
    SteeringResult,
    _classify,
)


# ── Classification tests ──────────────────────────────────────────────

def test_classify_continue_chinese():
    intent, label = _classify("继续执行任务")
    assert intent == SteeringIntent.CONTINUE
    assert label == "继续"


def test_classify_continue_english():
    intent, _ = _classify("go on please")
    assert intent == SteeringIntent.CONTINUE


def test_classify_continue_ok():
    intent, _ = _classify("好的，继续")
    assert intent == SteeringIntent.CONTINUE


def test_classify_pause_chinese():
    intent, label = _classify("暂停一下")
    assert intent == SteeringIntent.PAUSE
    assert label == "暂停"


def test_classify_pause_english():
    intent, _ = _classify("stop the task")
    assert intent == SteeringIntent.PAUSE


def test_classify_pause_wait():
    intent, _ = _classify("等一下")
    assert intent == SteeringIntent.PAUSE


def test_classify_change_goal():
    intent, label = _classify("改成只改文档")
    assert intent == SteeringIntent.CHANGE_GOAL
    assert label == "变更目标"


def test_classify_change_goal_variant():
    intent, _ = _classify("换个需求")
    assert intent == SteeringIntent.CHANGE_GOAL


def test_classify_request_review():
    intent, label = _classify("帮我检查一下代码")
    assert intent == SteeringIntent.REQUEST_REVIEW
    assert label == "请求审查"


def test_classify_request_review_english():
    intent, _ = _classify("please review this")
    assert intent == SteeringIntent.REQUEST_REVIEW


def test_classify_abort():
    intent, label = _classify("取消任务")
    assert intent == SteeringIntent.ABORT
    assert label == "中止"


def test_classify_abort_terminate():
    intent, _ = _classify("终止所有操作")
    assert intent == SteeringIntent.ABORT


def test_classify_unknown_gibberish():
    intent, label = _classify("asdfghjkl")
    assert intent == SteeringIntent.UNKNOWN
    assert label == "无法识别"


def test_classify_unknown_empty():
    intent, _ = _classify("")
    assert intent == SteeringIntent.UNKNOWN


def test_classify_unknown_vague():
    intent, _ = _classify("嗯...")
    assert intent == SteeringIntent.UNKNOWN


def test_classify_priority_abort_over_pause():
    """'取消暂停' should match abort (first in rule order)."""
    intent, _ = _classify("取消暂停")
    assert intent == SteeringIntent.ABORT


# ── Service process tests ─────────────────────────────────────────────

def test_process_continue():
    svc = HumanSteeringService()
    result = svc.process("run_1", "继续执行")
    assert result.intent == "continue"
    assert result.requires_human_confirmation is False
    assert result.explanation != ""
    assert "继续" in result.explanation


def test_process_pause_without_m66():
    """Without M66 integration, pause records intent gracefully."""
    svc = HumanSteeringService()
    result = svc.process("run_2", "暂停")
    assert result.intent == "pause"
    assert result.requires_human_confirmation is False


def test_process_change_goal_is_pending():
    """change_goal must require human confirmation and NOT execute."""
    svc = HumanSteeringService()
    result = svc.process("run_3", "改成只修bug")
    assert result.intent == "change_goal"
    assert result.requires_human_confirmation is True
    assert len(result.pending_actions) > 0
    assert "二次确认" in result.explanation


def test_process_abort_is_pending():
    """abort must require human confirmation and NOT execute."""
    svc = HumanSteeringService()
    result = svc.process("run_4", "放弃任务")
    assert result.intent == "abort"
    assert result.requires_human_confirmation is True
    assert len(result.pending_actions) > 0
    assert "二次确认" in result.explanation


def test_process_request_review():
    svc = HumanSteeringService()
    result = svc.process("run_5", "帮我review一下")
    assert result.intent == "request_review"
    assert result.requires_human_confirmation is False


def test_process_unknown_has_degradation():
    """Unknown intent must return Chinese degradation message."""
    svc = HumanSteeringService()
    result = svc.process("run_6", "blahblah")
    assert result.intent == "unknown"
    assert "无法识别" in result.explanation
    assert "继续" in result.explanation or "暂停" in result.explanation  # guidance


def test_process_all_chinese_explanations():
    """Every result must have a non-empty Chinese explanation."""
    svc = HumanSteeringService()
    inputs = ["继续", "暂停", "改成xxx", "检查一下", "取消", "???"]
    for content in inputs:
        result = svc.process("run_x", content)
        assert result.explanation, f"explanation empty for: {content}"
        assert result.intent_label, f"intent_label empty for: {content}"
        assert result.action_taken, f"action_taken empty for: {content}"


def test_process_evidence_ref_generated():
    """Every result must have a unique evidence ref."""
    svc = HumanSteeringService()
    result = svc.process("run_7", "继续")
    assert result.evidence_ref.startswith("steering_")
    assert len(result.evidence_ref) > 10


def test_process_timestamp_set():
    svc = HumanSteeringService()
    result = svc.process("run_8", "继续")
    assert result.timestamp > 0


def test_process_requires_human_confirmation_field():
    """Every result must have requires_human_confirmation boolean."""
    svc = HumanSteeringService()
    for content in ["继续", "暂停", "改成xxx", "检查", "取消", "???"]:
        result = svc.process("run_x", content)
        assert isinstance(result.requires_human_confirmation, bool), \
            f"requires_human_confirmation not bool for: {content}"


# ── Safety invariants ─────────────────────────────────────────────────

def test_never_calls_approve_permission():
    """HumanSteeringService must have no dependency on approve_permission."""
    svc = HumanSteeringService()
    # The service class itself has no approve_permission method or reference
    assert not hasattr(svc, "approve_permission")
    assert "approve_permission" not in dir(svc)


def test_to_dict_contains_all_fields():
    svc = HumanSteeringService()
    result = svc.process("run_9", "继续")
    d = result.to_dict()
    required = ["intent", "intent_label", "explanation", "requires_human_confirmation",
                "action_taken", "pending_actions", "evidence_ref", "timestamp"]
    for key in required:
        assert key in d, f"missing field: {key}"


# ── M66 integration tests ─────────────────────────────────────────────

def test_pause_with_m66_integration():
    """Pause steering with M66 should delegate to PauseResumeService."""
    from bolt_core.pause_resume import PauseResumeService
    pause_svc = PauseResumeService()
    svc = HumanSteeringService(pause_service=pause_svc)
    result = svc.process("run_p", "暂停", current_node_id="node_a", current_status="running")
    assert result.intent == "pause"
    assert "M66" in result.explanation or "快照" in result.explanation
    # Verify M66 did pause
    assert pause_svc.is_paused("node_a") is True


def test_pause_m66_wrong_state_graceful():
    """Pause on already-paused node should be rejected gracefully, not crash."""
    from bolt_core.pause_resume import PauseResumeService
    pause_svc = PauseResumeService()
    pause_svc.pause("node_b", "running")
    svc = HumanSteeringService(pause_service=pause_svc)
    result = svc.process("run_p2", "暂停", current_node_id="node_b", current_status="running")
    assert result.intent == "pause"
    # Should be rejected by M66 (already paused), fallback gracefully
    assert "拒绝" in result.explanation or "暂停未执行" in result.action_taken


def test_pause_m66_invalid_state_graceful():
    """Pause from completed state should be rejected gracefully."""
    from bolt_core.pause_resume import PauseResumeService
    pause_svc = PauseResumeService()
    svc = HumanSteeringService(pause_service=pause_svc)
    result = svc.process("run_p3", "暂停", current_node_id="node_c", current_status="completed")
    assert result.intent == "pause"
    # Should be rejected (completed is not pausable)
    assert "拒绝" in result.explanation or "暂停未执行" in result.action_taken


def test_evidence_callback():
    """Evidence callback should be called on each process."""
    calls = []

    def record(run_id, result):
        calls.append((run_id, result.intent))

    svc = HumanSteeringService(record_evidence=record)
    svc.process("run_ev", "继续")
    assert len(calls) == 1
    assert calls[0] == ("run_ev", "continue")


def test_evidence_callback_failure_does_not_block():
    """If evidence recording fails, steering should still succeed."""
    def failing_record(run_id, result):
        raise RuntimeError("simulated failure")

    svc = HumanSteeringService(record_evidence=failing_record)
    result = svc.process("run_ev2", "继续")
    assert result.intent == "continue"  # should still work
