"""Tests for DecisionMemoryService."""
import pytest
import tempfile
from pathlib import Path

from bolt_core.decision_memory import (
    DecisionMemoryService,
    DecisionRecord,
    _is_safe_path,
)


# ── DecisionRecord ─────────────────────────────────────────────────────

def test_decision_record_fields():
    r = DecisionRecord(
        decision_id="072-code-map-index",
        milestone="M72",
        title="M72 Code Map Index — 设计决策",
        summary_cn="Agent 需要理解项目代码结构",
        rationale="静态解析安全快速无副作用",
        tradeoffs="AST 解析对大文件可能有性能开销",
        outcome="已实现，19 tests 通过",
        source_refs=["docs/decisions/072-code-map-index.md"],
    )
    d = r.to_dict()
    assert d["decision_id"] == "072-code-map-index"
    assert d["milestone"] == "M72"
    assert d["title"] == "M72 Code Map Index — 设计决策"
    assert d["summary_cn"] == "Agent 需要理解项目代码结构"
    assert d["rationale"] == "静态解析安全快速无副作用"
    assert d["tradeoffs"] == "AST 解析对大文件可能有性能开销"
    assert d["outcome"] == "已实现，19 tests 通过"
    assert d["source_refs"] == ["docs/decisions/072-code-map-index.md"]


def test_decision_record_is_frozen():
    r = DecisionRecord(
        decision_id="test", milestone="M1", title="T", summary_cn="S",
        rationale="R", tradeoffs="T", outcome="O", source_refs=["ref"]
    )
    with pytest.raises(Exception):
        r.decision_id = "changed"  # type: ignore[misc]


# ── Service: initialization ────────────────────────────────────────────

def test_service_creates_with_workspace():
    svc = DecisionMemoryService(".")
    assert svc._workspace is not None
    assert svc._decisions_dir is not None


def test_service_lists_decisions():
    svc = DecisionMemoryService(".")
    records = svc.list_all()
    assert isinstance(records, list)
    # Should have at least 60 decisions from M0-M72
    assert len(records) >= 60, f"Expected ≥60 decisions, got {len(records)}"


def test_service_all_records_are_decisionrecord():
    svc = DecisionMemoryService(".")
    for r in svc.list_all():
        assert isinstance(r, DecisionRecord)


# ── Service: get_detail ────────────────────────────────────────────────

def test_get_detail_returns_record():
    svc = DecisionMemoryService(".")
    record = svc.get_detail("072-code-map-index")
    assert record is not None
    assert record.decision_id == "072-code-map-index"
    assert record.milestone == "M72"
    assert record.title != ""
    assert record.summary_cn != ""
    assert len(record.source_refs) > 0


def test_get_detail_unknown_id():
    svc = DecisionMemoryService(".")
    record = svc.get_detail("nonexistent-decision-id")
    assert record is None


# ── Service: query by milestone ────────────────────────────────────────

def test_query_by_milestone_m70():
    svc = DecisionMemoryService(".")
    results = svc.query_by_milestone("M70")
    assert isinstance(results, list)
    # M70 should exist
    assert len(results) >= 1, f"Expected ≥1 M70 decisions, got {len(results)}"


def test_query_by_milestone_m71():
    svc = DecisionMemoryService(".")
    results = svc.query_by_milestone("M71")
    assert len(results) >= 1


def test_query_by_milestone_m72():
    svc = DecisionMemoryService(".")
    results = svc.query_by_milestone("M72")
    assert len(results) >= 1


def test_query_by_milestone_nonexistent():
    svc = DecisionMemoryService(".")
    results = svc.query_by_milestone("M999")
    assert results == []


# ── Service: query by keyword ──────────────────────────────────────────

def test_query_by_keyword_security():
    svc = DecisionMemoryService(".")
    results = svc.query_by_keyword("安全")
    assert isinstance(results, list)
    # There should be security-related decisions
    assert len(results) >= 1


def test_query_by_keyword_permission():
    svc = DecisionMemoryService(".")
    results = svc.query_by_keyword("Permission")
    assert isinstance(results, list)


def test_query_by_keyword_no_match():
    svc = DecisionMemoryService(".")
    results = svc.query_by_keyword("xyznonexistent12345")
    assert results == []


# ── Service: source_refs ───────────────────────────────────────────────

def test_all_records_have_source_refs():
    svc = DecisionMemoryService(".")
    for r in svc.list_all():
        assert len(r.source_refs) > 0, f"Missing source_refs for {r.decision_id}"
        assert any("docs/decisions/" in s for s in r.source_refs), \
            f"source_refs should point to docs/decisions/: {r.source_refs}"


def test_records_have_chinese_content():
    svc = DecisionMemoryService(".")
    chinese_count = 0
    for r in svc.list_all():
        text = r.title + r.summary_cn + r.rationale
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            chinese_count += 1
    # Most decisions should have Chinese content
    assert chinese_count >= len(svc.list_all()) * 0.3, \
        f"Expected ≥30% Chinese decisions, got {chinese_count}/{len(svc.list_all())}"


# ── Service: empty directory ───────────────────────────────────────────

def test_empty_decisions_dir():
    with tempfile.TemporaryDirectory() as tmp:
        svc = DecisionMemoryService(tmp)
        records = svc.list_all()
        assert records == []


# ── Service: no secrets in output ──────────────────────────────────────

def test_no_secret_in_decision_output():
    svc = DecisionMemoryService(".")
    for r in svc.list_all():
        d = r.to_dict()
        text = str(d).lower()
        # Check for actual secret patterns (not substrings in words like "task-closure")
        import re
        # API key patterns: sk- followed by alphanum (OpenAI), AKIA (AWS)
        assert not re.search(r'sk-[a-z0-9]{20,}', text), f"API key pattern in {r.decision_id}"
        assert not re.search(r'akia[a-z0-9]{16}', text), f"AWS key pattern in {r.decision_id}"
        # "private key" may appear in security rule descriptions; check for actual
        # key material patterns (PEM headers)
        assert not re.search(r'-----begin\s+(rsa\s+)?private\s+key', text), \
            f"PEM private key in {r.decision_id}"
        # password value patterns
        assert not re.search(r'password\s*[:=]\s*[^\s\[已]{3,}', text), \
            f"password value in {r.decision_id}"


# ── Service: summary endpoint data ─────────────────────────────────────

def test_summary_like_data():
    """Verify structure similar to what /decisions/summary would return."""
    svc = DecisionMemoryService(".")
    records = svc.list_all()
    milestones: dict[str, int] = {}
    for r in records:
        m = r.milestone
        milestones[m] = milestones.get(m, 0) + 1
    assert len(milestones) > 0
    assert sum(milestones.values()) == len(records)


# ── _is_safe_path ──────────────────────────────────────────────────────

def test_is_safe_rejects_env():
    assert not _is_safe_path(Path("/tmp/.env"))


def test_is_safe_rejects_node_modules():
    assert not _is_safe_path(Path("/tmp/node_modules/foo.md"))


def test_is_safe_accepts_normal():
    assert _is_safe_path(Path("/tmp/docs/decisions/test.md"))


def test_is_safe_rejects_credentials():
    assert not _is_safe_path(Path("/tmp/credentials.json"))


def test_is_safe_rejects_private_key():
    assert not _is_safe_path(Path("/tmp/private.key"))
