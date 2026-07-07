"""Execution state machine for task nodes. Manages state transitions only; never auto-executes."""
from __future__ import annotations

# ── State definitions ──
STATES = {"pending", "ready", "running", "waiting_permission", "paused", "completed", "failed", "blocked"}
TERMINAL_STATES = {"completed", "failed"}

# ── Valid transitions ──
TRANSITIONS: dict[str, set[str]] = {
    "pending": {"ready", "blocked"},
    "ready": {"running", "blocked"},
    "running": {"waiting_permission", "completed", "failed", "paused"},
    "waiting_permission": {"running", "failed", "blocked"},
    "paused": {"ready", "failed"},
    "blocked": {"pending"},
    "completed": set(),  # terminal
    "failed": set(),     # terminal
}

# ── State labels (Chinese) ──
STATE_LABELS: dict[str, str] = {
    "pending": "待处理",
    "ready": "就绪",
    "running": "执行中",
    "waiting_permission": "等待权限",
    "paused": "已暂停",
    "completed": "已完成",
    "failed": "已失败",
    "blocked": "已阻塞",
}


class ExecutionStateMachine:
    """Validates and manages state transitions for execution nodes.
    Does NOT execute anything — only enforces transition rules.
    Designed to coexist with task closure, execution queue, and PermissionGate.
    """

    @staticmethod
    def valid_states() -> list[str]:
        return sorted(STATES)

    @staticmethod
    def terminal_states() -> list[str]:
        return sorted(TERMINAL_STATES)

    @staticmethod
    def allowed_transitions(from_state: str) -> list[str]:
        """Return list of valid next states from a given state."""
        if from_state not in TRANSITIONS:
            raise ValueError(f"unknown state: {from_state}")
        return sorted(TRANSITIONS[from_state])

    @staticmethod
    def can_transition(from_state: str, to_state: str) -> bool:
        """Check if a transition is valid."""
        if from_state not in TRANSITIONS:
            return False
        return to_state in TRANSITIONS[from_state]

    @staticmethod
    def validate_transition(from_state: str, to_state: str) -> None:
        """Raise ValueError if the transition is invalid."""
        if from_state not in STATES:
            raise ValueError(f"unknown state: {from_state}, valid states: {STATES}")
        if to_state not in STATES:
            raise ValueError(f"unknown state: {to_state}, valid states: {STATES}")
        allowed = TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            labels = [f"{s}({STATE_LABELS.get(s, s)})" for s in sorted(allowed)]
            raise ValueError(
                f"invalid transition: {STATE_LABELS.get(from_state, from_state)} -> {STATE_LABELS.get(to_state, to_state)}. "
                f"允许的转换：{', '.join(labels) if labels else '无（终端状态）'}"
            )

    @staticmethod
    def is_terminal(state: str) -> bool:
        return state in TERMINAL_STATES

    @staticmethod
    def label(state: str) -> str:
        """Return Chinese label for a state."""
        return STATE_LABELS.get(state, state)

    @staticmethod
    def state_summary() -> dict:
        """Return a summary of all states and their labels."""
        return {
            "states": {s: STATE_LABELS.get(s, s) for s in sorted(STATES)},
            "terminal": sorted(TERMINAL_STATES),
            "transitions": {s: sorted(t) for s, t in sorted(TRANSITIONS.items())},
        }


def transition(node_id: str, from_state: str, to_state: str, reason: str = "") -> dict:
    """Validate and record a state transition. Returns a transition event dict."""
    ExecutionStateMachine.validate_transition(from_state, to_state)
    return {
        "node_id": node_id,
        "from_state": from_state,
        "to_state": to_state,
        "from_label": STATE_LABELS.get(from_state, from_state),
        "to_label": STATE_LABELS.get(to_state, to_state),
        "reason": reason,
        "valid": True,
    }
