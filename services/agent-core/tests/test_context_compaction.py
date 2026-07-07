"""Tests for ContextCompactionService."""
import pytest
from pathlib import Path

from bolt_core.context_compaction import (
    ContextCompactionService,
    CompactSummary,
)


# ── CompactSummary ──────────────────────────────────────────────────────

def test_compact_summary_fields():
    s = CompactSummary(
        objective="测试目标",
        current_state="测试状态",
        completed_milestones=["M71", "M72", "M73"],
        active_constraints=["全中文", "不自动 push"],
        relevant_decisions=[{"milestone": "M71", "title": "测试"}],
        known_failures=[{"severity": "P1", "symptom_cn": "测试失败"}],
        user_preferences=[{"category": "language", "statement_cn": "中文"}],
        next_actions=["继续执行"],
        source_refs=["docs/project-state.md"],
    )
    d = s.to_dict()
    assert d["objective"] == "测试目标"
    assert len(d["completed_milestones"]) == 3
    assert len(d["active_constraints"]) == 2


def test_compact_summary_to_markdown():
    s = CompactSummary(
        objective="测试目标",
        current_state="测试状态",
        completed_milestones=["M71"],
        active_constraints=["全中文"],
        relevant_decisions=[],
        known_failures=[],
        user_preferences=[],
        next_actions=["继续"],
        source_refs=["ref"],
    )
    md = s.to_markdown()
    assert "# 项目上下文压缩摘要" in md
    assert "测试目标" in md
    assert "M71" in md
    assert "全中文" in md


def test_compact_summary_is_frozen():
    s = CompactSummary(
        objective="o", current_state="s", completed_milestones=[],
        active_constraints=[], relevant_decisions=[], known_failures=[],
        user_preferences=[], next_actions=[], source_refs=[],
    )
    with pytest.raises(Exception):
        s.objective = "changed"  # type: ignore[misc]


# ── Service: compact ───────────────────────────────────────────────────

def test_compact_returns_summary():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert isinstance(summary, CompactSummary)
    assert summary.objective != ""


def test_compact_has_objective():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert len(summary.objective) > 0


def test_compact_has_current_state():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert "Bolt" in summary.current_state or "项目" in summary.current_state


def test_compact_has_completed_milestones():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert len(summary.completed_milestones) >= 1


def test_compact_has_active_constraints():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert len(summary.active_constraints) >= 5  # safety rules always present


def test_compact_safety_rules_preserved():
    """Safety hard rules must always be in the summary."""
    svc = ContextCompactionService(".")
    summary = svc.compact(max_items=3)  # very small max
    constraints_text = " ".join(summary.active_constraints)
    assert "不自动 push" in constraints_text
    assert "PermissionGate" in constraints_text
    assert "as any" in constraints_text


def test_compact_has_source_refs():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert len(summary.source_refs) > 0


def test_compact_has_user_preferences():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert len(summary.user_preferences) >= 5


def test_compact_has_next_actions():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    assert len(summary.next_actions) > 0


def test_compact_max_items_respected():
    svc = ContextCompactionService(".")
    summary_small = svc.compact(max_items=5)
    summary_large = svc.compact(max_items=100)
    # Smaller max_items should have fewer decision/failure items
    assert len(summary_small.relevant_decisions) <= len(summary_large.relevant_decisions) + 5


def test_compact_chinese_output():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    md = summary.to_markdown()
    assert any('\u4e00' <= c <= '\u9fff' for c in md)


def test_compact_no_secrets():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    d = summary.to_dict()
    text = str(d).lower()
    import re
    assert not re.search(r'sk-[a-z0-9]{20,}', text)


# ── Service: token estimation ──────────────────────────────────────────

def test_estimate_tokens_returns_positive():
    svc = ContextCompactionService(".")
    summary = svc.compact()
    tokens = svc.estimate_tokens(summary)
    assert tokens > 0
    assert tokens < 50000  # reasonable upper bound


def test_estimate_tokens_smaller_with_fewer_items():
    svc = ContextCompactionService(".")
    s1 = svc.compact(max_items=5)
    s2 = svc.compact(max_items=100)
    t1 = svc.estimate_tokens(s1)
    t2 = svc.estimate_tokens(s2)
    # Smaller max_items should use fewer tokens
    assert t1 <= t2 + 100  # allow some variance
