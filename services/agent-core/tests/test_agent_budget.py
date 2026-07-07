"""Unit tests for AgentBudgetService. All four dimensions, Chinese messages, safety."""
import pytest

from bolt_core.agent_budget import (
    AgentBudgetService,
    BudgetConfig,
    BudgetState,
    BudgetResult,
    _DEFAULT_MAX_STEPS,
    _DEFAULT_MAX_TOOL_CALLS,
    _DEFAULT_MAX_RUNTIME_SECONDS,
    _DEFAULT_MAX_CONTEXT_TOKENS,
)


# ── BudgetConfig tests ────────────────────────────────────────────────

def test_config_defaults():
    cfg = BudgetConfig()
    assert cfg.max_steps == _DEFAULT_MAX_STEPS
    assert cfg.max_tool_calls == _DEFAULT_MAX_TOOL_CALLS
    assert cfg.max_runtime_seconds == _DEFAULT_MAX_RUNTIME_SECONDS
    assert cfg.max_context_tokens == _DEFAULT_MAX_CONTEXT_TOKENS


def test_config_from_dict_partial():
    cfg = BudgetConfig.from_dict({"max_steps": 10})
    assert cfg.max_steps == 10
    assert cfg.max_tool_calls == _DEFAULT_MAX_TOOL_CALLS  # default


def test_config_from_dict_none():
    cfg = BudgetConfig.from_dict(None)
    assert cfg.max_steps == _DEFAULT_MAX_STEPS


def test_config_to_dict():
    cfg = BudgetConfig(max_steps=20)
    d = cfg.to_dict()
    assert d["max_steps"] == 20
    assert "max_tool_calls" in d


# ── BudgetState tests ─────────────────────────────────────────────────

def test_state_defaults():
    st = BudgetState()
    assert st.steps_used == 0
    assert st.tool_calls_used == 0
    assert st.elapsed_seconds == 0.0
    assert st.context_tokens_used == 0


def test_state_to_dict():
    st = BudgetState(steps_used=5, tool_calls_used=3)
    d = st.to_dict()
    assert d["steps_used"] == 5
    assert d["tool_calls_used"] == 3


# ── Check: allowed ────────────────────────────────────────────────────

def test_check_allowed():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=10, max_tool_calls=20)
    st = BudgetState(steps_used=5, tool_calls_used=10)
    result = svc.check(cfg, st)
    assert result.allowed is True
    assert "通过" in result.explanation


def test_check_allowed_at_boundary_minus_one():
    """One below limit should be allowed."""
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=10)
    st = BudgetState(steps_used=9)
    result = svc.check(cfg, st)
    assert result.allowed is True


# ── Check: blocked - steps ────────────────────────────────────────────

def test_check_blocked_steps():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=10)
    st = BudgetState(steps_used=10)
    result = svc.check(cfg, st)
    assert result.allowed is False
    assert result.dimension == "steps"
    assert "步数" in result.explanation
    assert result.suggestion != ""


def test_check_blocked_steps_exceeded():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=5)
    st = BudgetState(steps_used=20)
    result = svc.check(cfg, st)
    assert result.allowed is False
    assert result.dimension == "steps"


# ── Check: blocked - tool calls ───────────────────────────────────────

def test_check_blocked_tool_calls():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=100, max_tool_calls=5)
    st = BudgetState(steps_used=1, tool_calls_used=5)
    result = svc.check(cfg, st)
    assert result.allowed is False
    assert result.dimension == "tool_calls"
    assert "工具调用" in result.explanation


# ── Check: blocked - runtime ──────────────────────────────────────────

def test_check_blocked_runtime():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_runtime_seconds=60)
    st = BudgetState(elapsed_seconds=60.1)
    result = svc.check(cfg, st)
    assert result.allowed is False
    assert result.dimension == "runtime"
    assert "运行时间" in result.explanation


def test_check_blocked_runtime_at_boundary():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_runtime_seconds=60)
    st = BudgetState(elapsed_seconds=60.0)
    result = svc.check(cfg, st)
    assert result.allowed is False


# ── Check: blocked - context tokens ───────────────────────────────────

def test_check_blocked_context_tokens():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_context_tokens=4000)
    st = BudgetState(context_tokens_used=4000)
    result = svc.check(cfg, st)
    assert result.allowed is False
    assert result.dimension == "context_tokens"
    assert "token" in result.explanation.lower()


# ── Check: first violation wins ───────────────────────────────────────

def test_check_first_violation_wins():
    """Steps checked first — if both steps and tool_calls exceed, steps wins."""
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=5, max_tool_calls=5)
    st = BudgetState(steps_used=10, tool_calls_used=10)
    result = svc.check(cfg, st)
    assert result.allowed is False
    assert result.dimension == "steps"


# ── Chinese message tests ─────────────────────────────────────────────

def test_all_blocked_messages_chinese():
    """All blocked explanations must contain Chinese characters."""
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=1, max_tool_calls=1,
                       max_runtime_seconds=1, max_context_tokens=1)
    st = BudgetState(steps_used=5)
    r1 = svc.check(cfg, st)
    assert any('\u4e00' <= c <= '\u9fff' for c in r1.explanation)

    st2 = BudgetState(steps_used=0, tool_calls_used=5)
    r2 = svc.check(cfg, st2)
    assert any('\u4e00' <= c <= '\u9fff' for c in r2.explanation)

    st3 = BudgetState(elapsed_seconds=5)
    r3 = svc.check(cfg, st3)
    assert any('\u4e00' <= c <= '\u9fff' for c in r3.explanation)

    st4 = BudgetState(context_tokens_used=5)
    r4 = svc.check(cfg, st4)
    assert any('\u4e00' <= c <= '\u9fff' for c in r4.explanation)


# ── Result shape ──────────────────────────────────────────────────────

def test_result_to_dict():
    svc = AgentBudgetService()
    result = svc.check(BudgetConfig(), BudgetState())
    d = result.to_dict()
    for key in ["allowed", "dimension", "explanation", "suggestion", "config", "state"]:
        assert key in d, f"missing: {key}"


def test_blocked_result_has_suggestion():
    svc = AgentBudgetService()
    cfg = BudgetConfig(max_steps=1)
    st = BudgetState(steps_used=5)
    result = svc.check(cfg, st)
    assert result.suggestion != ""


# ── check_single tests ────────────────────────────────────────────────

def test_check_single_allowed():
    svc = AgentBudgetService()
    result = svc.check_single("steps", 5, 10, "步数")
    assert result.allowed is True


def test_check_single_blocked():
    svc = AgentBudgetService()
    result = svc.check_single("steps", 10, 10, "步数")
    assert result.allowed is False
    assert result.dimension == "steps"


def test_check_single_chinese_label():
    svc = AgentBudgetService()
    result = svc.check_single("runtime", 100, 50, "运行时间")
    assert result.allowed is False
    assert "运行时间" in result.explanation


# ── Safety invariants ─────────────────────────────────────────────────

def test_service_has_no_auto_increase():
    """AgentBudgetService must have no method to increase budget."""
    svc = AgentBudgetService()
    assert not hasattr(svc, "increase_budget")
    assert not hasattr(svc, "raise_limit")


def test_service_has_no_auto_continue():
    """AgentBudgetService must have no method to continue execution."""
    svc = AgentBudgetService()
    assert not hasattr(svc, "continue")
    assert not hasattr(svc, "resume")


def test_defaults_are_safe():
    """Default limits should be reasonable (not infinite, not zero)."""
    cfg = BudgetConfig()
    assert 1 <= cfg.max_steps <= 10000
    assert 1 <= cfg.max_tool_calls <= 100000
    assert 1 <= cfg.max_runtime_seconds <= 86400
    assert 1 <= cfg.max_context_tokens <= 1000000
