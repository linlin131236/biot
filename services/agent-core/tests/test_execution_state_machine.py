"""Unit tests for ExecutionStateMachine. Validation only, no auto-execution."""
import pytest

from bolt_core.execution_state_machine import (
    STATES, TERMINAL_STATES, TRANSITIONS, STATE_LABELS,
    ExecutionStateMachine, transition,
)


def test_valid_transitions_are_legal():
    """All transitions in TRANSITIONS use valid states."""
    for from_state, to_states in TRANSITIONS.items():
        assert from_state in STATES
        for to_state in to_states:
            assert to_state in STATES


def test_terminal_states_have_no_exits():
    """Terminal states (completed, failed) have no outgoing transitions."""
    for ts in TERMINAL_STATES:
        assert TRANSITIONS[ts] == set()


def test_transition_pending_to_ready():
    """pending -> ready is valid."""
    result = transition("n1", "pending", "ready", "依赖已满足")
    assert result["valid"] is True
    assert result["to_state"] == "ready"


def test_transition_running_to_waiting_permission():
    """running -> waiting_permission is valid."""
    result = transition("n1", "running", "waiting_permission", "需要人工批准")
    assert result["valid"] is True


def test_transition_running_to_paused():
    """running -> paused is valid."""
    result = transition("n1", "running", "paused", "用户暂停")
    assert result["valid"] is True


def test_transition_completed_is_terminal():
    """completed -> anything raises ValueError."""
    with pytest.raises(ValueError, match="invalid transition"):
        transition("n1", "completed", "running")


def test_transition_failed_is_terminal():
    """failed -> anything raises ValueError."""
    with pytest.raises(ValueError, match="invalid transition"):
        transition("n1", "failed", "pending")


def test_transition_pending_to_completed_invalid():
    """pending -> completed is not allowed (must go through running)."""
    with pytest.raises(ValueError, match="invalid transition"):
        transition("n1", "pending", "completed")


def test_transition_waiting_permission_to_completed_invalid():
    """waiting_permission -> completed is not allowed (must go through running)."""
    with pytest.raises(ValueError, match="invalid transition"):
        transition("n1", "waiting_permission", "completed")


def test_unknown_from_state_raises():
    """Unknown from_state raises ValueError."""
    with pytest.raises(ValueError, match="unknown state"):
        transition("n1", "gibberish", "ready")


def test_unknown_to_state_raises():
    """Unknown to_state raises ValueError."""
    with pytest.raises(ValueError, match="unknown state"):
        transition("n1", "pending", "gibberish")


def test_can_transition_returns_bool():
    """can_transition returns True/False without raising."""
    assert ExecutionStateMachine.can_transition("pending", "ready") is True
    assert ExecutionStateMachine.can_transition("pending", "completed") is False
    assert ExecutionStateMachine.can_transition("completed", "anything") is False


def test_allowed_transitions_lists_next():
    """allowed_transitions returns valid next states."""
    allowed = ExecutionStateMachine.allowed_transitions("pending")
    assert "ready" in allowed
    assert "blocked" in allowed
    assert "completed" not in allowed


def test_is_terminal():
    """is_terminal correctly identifies terminal states."""
    assert ExecutionStateMachine.is_terminal("completed") is True
    assert ExecutionStateMachine.is_terminal("failed") is True
    assert ExecutionStateMachine.is_terminal("running") is False


def test_label_returns_chinese():
    """label returns Chinese text for known states."""
    assert ExecutionStateMachine.label("pending") == "待处理"
    assert ExecutionStateMachine.label("running") == "执行中"
    assert ExecutionStateMachine.label("waiting_permission") == "等待权限"


def test_state_summary_covers_all():
    """state_summary includes all states and transitions."""
    summary = ExecutionStateMachine.state_summary()
    assert len(summary["states"]) == len(STATES)
    assert len(summary["transitions"]) == len(TRANSITIONS)
    assert set(summary["terminal"]) == TERMINAL_STATES


def test_valid_states_and_terminal():
    """valid_states and terminal_states return correct data."""
    assert set(ExecutionStateMachine.valid_states()) == STATES
    assert set(ExecutionStateMachine.terminal_states()) == TERMINAL_STATES


def test_no_auto_execution():
    """State machine has no execution methods."""
    methods = [m for m in dir(ExecutionStateMachine) if not m.startswith("_")]
    for m in methods:
        assert "execute" not in m.lower()
        assert "approve" not in m.lower()
        assert "run" not in m.lower()
        assert "shell" not in m.lower()
