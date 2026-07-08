"""Tests for ThreadHandoffSummaryService."""
import pytest

from bolt_core.thread_handoff_summary import (
    ThreadHandoffSummaryService,
    HandoffSummary,
)


# ── HandoffSummary ─────────────────────────────────────────────────────

def test_handoff_summary_fields():
    s = HandoffSummary(
        workspace_dir="D:\\Bolt\\Bolt",
        head_state="abc1234 feat(M75): add user preference memory",
        origin_state="## main...origin/main",
        completed_milestones=["M71", "M72", "M73", "M74", "M75"],
        active_prohibitions=["不自动 push", "不绕过 PermissionGate"],
        required_docs=["docs/project-state.md"],
        latest_review_gate="docs/phase-75-review-gate.md",
        unresolved_risks=["M61 纯内存模型重启丢失"],
        next_steps=["等待用户确认"],
        source_refs=["docs/project-state.md"],
    )
    d = s.to_dict()
    assert d["workspace_dir"] == "D:\\Bolt\\Bolt"
    assert len(d["completed_milestones"]) == 5
    assert len(d["active_prohibitions"]) == 2


def test_handoff_summary_to_markdown():
    s = HandoffSummary(
        workspace_dir="/tmp/test",
        head_state="abc1234",
        origin_state="main",
        completed_milestones=["M71"],
        active_prohibitions=["不自动 push"],
        required_docs=["docs/project-state.md"],
        latest_review_gate="docs/phase-75-review-gate.md",
        unresolved_risks=["无"],
        next_steps=["继续"],
        source_refs=["ref"],
    )
    md = s.to_markdown()
    assert "# Bolt 项目接手摘要" in md
    assert "不自动执行" in md
    assert "不自动 push" in md
    assert "/tmp/test" in md


def test_handoff_summary_has_disclaimer():
    s = HandoffSummary(
        workspace_dir=".", head_state="h", origin_state="o",
        completed_milestones=[], active_prohibitions=["不自动 push"],
        required_docs=[], latest_review_gate="", unresolved_risks=[],
        next_steps=[], source_refs=[],
    )
    md = s.to_markdown()
    assert "不自动执行" in md
    assert "不自动 push" in md
    assert "不进入未授权 milestone" in md


def test_handoff_summary_is_frozen():
    s = HandoffSummary(
        workspace_dir=".", head_state="h", origin_state="o",
        completed_milestones=[], active_prohibitions=[],
        required_docs=[], latest_review_gate="", unresolved_risks=[],
        next_steps=[], source_refs=[],
    )
    with pytest.raises(Exception):
        s.workspace_dir = "changed"  # type: ignore[misc]


# ── Service: generate ──────────────────────────────────────────────────

def test_service_generates_summary():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    assert isinstance(summary, HandoffSummary)
    assert summary.workspace_dir != ""


def test_generate_has_workspace_dir():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    assert len(summary.workspace_dir) > 0


def test_generate_has_head_state():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    assert summary.head_state != ""


def test_generate_has_prohibitions():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    assert len(summary.active_prohibitions) >= 5
    prohibitions_text = " ".join(summary.active_prohibitions)
    assert "push" in prohibitions_text
    assert "PermissionGate" in prohibitions_text


def test_generate_has_required_docs():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    assert len(summary.required_docs) >= 2
    assert any("project-state" in d for d in summary.required_docs)


def test_generate_has_next_steps():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    assert len(summary.next_steps) >= 3


def test_generate_no_secrets():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    d = summary.to_dict()
    text = str(d).lower()
    import re
    assert not re.search(r'sk-[a-z0-9]{20,}', text)
    # "private key" may appear in prohibition descriptions; check for actual key patterns
    assert not re.search(r'-----begin\s+(rsa\s+)?private\s+key', text)


def test_generate_chinese_output():
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    md = summary.to_markdown()
    assert any('\u4e00' <= c <= '\u9fff' for c in md)


def test_generate_no_unauthorized_milestone():
    """Handoff must explicitly warn against entering unauthorized milestones."""
    svc = ThreadHandoffSummaryService(".")
    summary = svc.generate()
    text = " ".join(summary.active_prohibitions) + summary.to_markdown()
    assert "未授权" in text or "禁止" in text
