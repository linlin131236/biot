"""Tests for FailureMemoryIndexService."""
import pytest
import tempfile
from pathlib import Path

from bolt_core.failure_memory_index import (
    FailureMemoryIndexService,
    FailureRecord,
    _M64_CATEGORIES,
)


# ── FailureRecord ───────────────────────────────────────────────────────

def test_failure_record_fields():
    r = FailureRecord(
        failure_id="phase-57-p1",
        category="code_quality",
        severity="P1",
        milestone="M57",
        symptom_cn="release readiness 扫描误报已脱敏占位符",
        root_cause_cn="_scan_secrets 未排除 [已脱敏] 占位符",
        fix_summary_cn="排除已脱敏占位符，兼容 JSON escaped Unicode",
        verification="通过 targeted tests 验证",
        recurrence_risk="低",
        source_refs=["docs/phase-57-review-gate.md"],
    )
    d = r.to_dict()
    assert d["failure_id"] == "phase-57-p1"
    assert d["category"] == "code_quality"
    assert d["severity"] == "P1"
    assert d["milestone"] == "M57"
    assert len(d["source_refs"]) > 0


def test_failure_record_is_frozen():
    r = FailureRecord(
        failure_id="t", category="c", severity="P1", milestone="M1",
        symptom_cn="s", root_cause_cn="r", fix_summary_cn="f",
        verification="v", recurrence_risk="低", source_refs=["ref"],
    )
    with pytest.raises(Exception):
        r.category = "changed"  # type: ignore[misc]


# ── Service: initialization ────────────────────────────────────────────

def test_service_creates():
    svc = FailureMemoryIndexService(".")
    assert svc._workspace is not None


def test_service_lists_failures():
    svc = FailureMemoryIndexService(".")
    records = svc.list_all()
    assert isinstance(records, list)
    # Should have at least some records from review gates
    assert len(records) >= 1, f"Expected ≥1 failure records, got {len(records)}"
    for r in records:
        assert isinstance(r, FailureRecord)


# ── Service: get_detail ────────────────────────────────────────────────

def test_get_detail_unknown():
    svc = FailureMemoryIndexService(".")
    record = svc.get_detail("nonexistent-id")
    assert record is None


# ── Service: query by category ─────────────────────────────────────────

def test_query_by_category():
    svc = FailureMemoryIndexService(".")
    for cat in _M64_CATEGORIES:
        results = svc.query_by_category(cat)
        assert isinstance(results, list)
        for r in results:
            assert r.category == cat or cat in r.category


def test_query_by_category_nonexistent():
    svc = FailureMemoryIndexService(".")
    results = svc.query_by_category("nonexistent_category_xyz")
    assert results == []


# ── Service: query by keyword ──────────────────────────────────────────

def test_query_by_keyword():
    svc = FailureMemoryIndexService(".")
    # "修复" should appear in many fix records
    results = svc.query_by_keyword("修复")
    assert isinstance(results, list)


def test_query_by_keyword_no_match():
    svc = FailureMemoryIndexService(".")
    results = svc.query_by_keyword("xyznonexistent12345")
    assert results == []


# ── Service: source_refs ────────────────────────────────────────────────

def test_all_records_have_source_refs():
    svc = FailureMemoryIndexService(".")
    for r in svc.list_all():
        assert len(r.source_refs) > 0, f"Missing source_refs for {r.failure_id}"


# ── Service: Chinese content ────────────────────────────────────────────

def test_records_have_chinese_content():
    svc = FailureMemoryIndexService(".")
    chinese_count = 0
    total = 0
    for r in svc.list_all():
        total += 1
        text = r.symptom_cn + r.root_cause_cn + r.fix_summary_cn
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            chinese_count += 1
    if total > 0:
        assert chinese_count >= total * 0.5, \
            f"Expected ≥50% Chinese failures, got {chinese_count}/{total}"


# ── Service: no secrets ─────────────────────────────────────────────────

def test_no_secret_in_failure_output():
    svc = FailureMemoryIndexService(".")
    import re
    for r in svc.list_all():
        d = r.to_dict()
        text = str(d).lower()
        assert not re.search(r'sk-[a-z0-9]{20,}', text), f"API key in {r.failure_id}"
        assert not re.search(r'akia[a-z0-9]{16}', text), f"AWS key in {r.failure_id}"
        assert "private key" not in text


# ── Service: category alignment with M64 ────────────────────────────────

def test_categories_align_with_m64():
    """Failure records should use M64-compatible categories."""
    svc = FailureMemoryIndexService(".")
    for r in svc.list_all():
        assert r.category in _M64_CATEGORIES or r.category == "unknown", \
            f"Unknown category '{r.category}' in {r.failure_id}"


# ── Service: severity values ────────────────────────────────────────────

def test_severity_values():
    svc = FailureMemoryIndexService(".")
    valid_severities = {"P1", "P2", "P3"}
    for r in svc.list_all():
        assert r.severity in valid_severities, \
            f"Invalid severity '{r.severity}' in {r.failure_id}"


# ── Service: no auto-fix indicators ─────────────────────────────────────

def test_no_auto_fix_indicators():
    """Failure index is read-only - should not suggest auto-fix."""
    svc = FailureMemoryIndexService(".")
    for r in svc.list_all():
        d = r.to_dict()
        text = str(d).lower()
        # "auto_fix" or "自动修复" should not appear as capability
        assert "auto_fix_possible" not in text
