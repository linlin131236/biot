"""Tests for UserPreferenceMemoryService."""
import pytest
from pathlib import Path

from bolt_core.user_preference_memory import (
    UserPreferenceMemoryService,
    PreferenceRecord,
    _HARD_PREFERENCES,
    _CATEGORY_LABELS,
)


# ── PreferenceRecord ────────────────────────────────────────────────────

def test_preference_record_fields():
    r = PreferenceRecord(
        preference_id="pref-test",
        category="language",
        statement_cn="所有 UI 必须中文",
        confidence="confirmed",
        source_refs=["docs/project-state.md"],
        can_apply_automatically=True,
        requires_confirmation=False,
    )
    d = r.to_dict()
    assert d["preference_id"] == "pref-test"
    assert d["category"] == "language"
    assert d["statement_cn"] == "所有 UI 必须中文"
    assert d["confidence"] == "confirmed"
    assert d["source_refs"] == ["docs/project-state.md"]
    assert d["can_apply_automatically"] is True
    assert d["requires_confirmation"] is False


def test_preference_record_is_frozen():
    r = PreferenceRecord(
        preference_id="t", category="c", statement_cn="s", confidence="c",
        source_refs=["r"], can_apply_automatically=True, requires_confirmation=False,
    )
    with pytest.raises(Exception):
        r.statement_cn = "changed"  # type: ignore[misc]


# ── Service: initialization ────────────────────────────────────────────

def test_service_creates():
    svc = UserPreferenceMemoryService(".")
    assert svc is not None


# ── Service: list_all ──────────────────────────────────────────────────

def test_list_all_preferences():
    svc = UserPreferenceMemoryService(".")
    records = svc.list_all()
    assert len(records) >= 10, f"Expected ≥10 hard preferences, got {len(records)}"
    for r in records:
        assert isinstance(r, PreferenceRecord)


def test_all_preferences_have_source_refs():
    svc = UserPreferenceMemoryService(".")
    for r in svc.list_all():
        assert len(r.source_refs) > 0, f"Missing source_refs for {r.preference_id}"


def test_all_preferences_have_chinese():
    svc = UserPreferenceMemoryService(".")
    for r in svc.list_all():
        assert any('\u4e00' <= c <= '\u9fff' for c in r.statement_cn), \
            f"Missing Chinese in {r.preference_id}: {r.statement_cn}"


# ── Service: get_detail ────────────────────────────────────────────────

def test_get_detail_language_pref():
    svc = UserPreferenceMemoryService(".")
    record = svc.get_detail("pref-001-language")
    assert record is not None
    assert record.category == "language"
    assert "中文" in record.statement_cn


def test_get_detail_address_pref():
    svc = UserPreferenceMemoryService(".")
    record = svc.get_detail("pref-002-address")
    assert record is not None
    assert "用户" in record.statement_cn


def test_get_detail_safety_pref():
    svc = UserPreferenceMemoryService(".")
    record = svc.get_detail("pref-003-no-auto-push")
    assert record is not None
    assert record.category == "safety"
    assert "push" in record.statement_cn or "Push" in record.statement_cn


def test_get_detail_unknown():
    svc = UserPreferenceMemoryService(".")
    record = svc.get_detail("nonexistent")
    assert record is None


# ── Service: query by category ─────────────────────────────────────────

def test_query_by_category_safety():
    svc = UserPreferenceMemoryService(".")
    results = svc.query_by_category("safety")
    assert len(results) >= 3  # no-auto-push, no-auto-approve, no-commit-artifacts, renderer-safety


def test_query_by_category_workflow():
    svc = UserPreferenceMemoryService(".")
    results = svc.query_by_category("workflow")
    assert len(results) >= 2  # milestone-discipline, no-unauthorized-milestone


def test_query_by_category_nonexistent():
    svc = UserPreferenceMemoryService(".")
    results = svc.query_by_category("nonexistent")
    assert results == []


# ── Service: query by keyword ──────────────────────────────────────────

def test_query_by_keyword_chinese():
    svc = UserPreferenceMemoryService(".")
    results = svc.query_by_keyword("中文")
    assert len(results) >= 1


def test_query_by_keyword_push():
    svc = UserPreferenceMemoryService(".")
    results = svc.query_by_keyword("push")
    assert len(results) >= 1


def test_query_by_keyword_no_match():
    svc = UserPreferenceMemoryService(".")
    results = svc.query_by_keyword("xyznonexistent12345")
    assert results == []


# ── Service: conflict check ────────────────────────────────────────────

def test_check_conflicts_returns_list():
    svc = UserPreferenceMemoryService(".")
    conflicts = svc.check_conflicts()
    assert isinstance(conflicts, list)
    # Currently no conflicts expected in hard preferences


def test_conflicts_have_chinese_descriptions():
    svc = UserPreferenceMemoryService(".")
    conflicts = svc.check_conflicts()
    for c in conflicts:
        assert "description_cn" in c
        assert "recommendation_cn" in c


# ── Service: secret detection ──────────────────────────────────────────

def test_is_secret_detects_api_key():
    svc = UserPreferenceMemoryService(".")
    assert svc.is_secret_attempt("sk-abc123def456ghi789jkl012mno345pqr678stu") is True


def test_is_secret_detects_aws_key():
    svc = UserPreferenceMemoryService(".")
    assert svc.is_secret_attempt("AKIA1234567890ABCDEF") is True


def test_is_secret_detects_private_key():
    svc = UserPreferenceMemoryService(".")
    assert svc.is_secret_attempt("-----BEGIN PRIVATE KEY-----") is True


def test_is_secret_rejects_normal_text():
    svc = UserPreferenceMemoryService(".")
    assert svc.is_secret_attempt("所有 UI 必须中文") is False


def test_is_secret_rejects_empty():
    svc = UserPreferenceMemoryService(".")
    assert svc.is_secret_attempt("") is False


# ── Hard preferences integrity ─────────────────────────────────────────

def test_category_labels_complete():
    """All hard preference categories should have labels."""
    for p in _HARD_PREFERENCES:
        assert p.category in _CATEGORY_LABELS, \
            f"Missing category label for '{p.category}' in {p.preference_id}"


def test_no_duplicate_preference_ids():
    ids = [p.preference_id for p in _HARD_PREFERENCES]
    assert len(ids) == len(set(ids)), "Duplicate preference IDs found"


def test_no_secret_in_preferences():
    svc = UserPreferenceMemoryService(".")
    for r in svc.list_all():
        assert not svc.is_secret_attempt(r.statement_cn), \
            f"Secret pattern in {r.preference_id}"
        for ref in r.source_refs:
            assert not svc.is_secret_attempt(ref), \
                f"Secret pattern in source_refs of {r.preference_id}"


def test_safety_prefs_cannot_be_overridden():
    """Safety preferences should have can_apply_automatically=True (always active)."""
    svc = UserPreferenceMemoryService(".")
    safety_prefs = svc.query_by_category("safety")
    for p in safety_prefs:
        # Safety prefs should be auto-applied
        assert p.can_apply_automatically, \
            f"Safety pref {p.preference_id} should be auto-applied"
        # Safety prefs should NOT require per-use confirmation
        assert not p.requires_confirmation, \
            f"Safety pref {p.preference_id} should not require per-use confirmation"
