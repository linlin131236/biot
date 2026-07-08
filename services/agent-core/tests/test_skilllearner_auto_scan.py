"""Tests for SkillLearner auto_scan (M162)."""
import pytest

from bolt_core.skilllearner_review_loop import SkillLearnerReviewLoopService


def test_auto_scan_without_failure_memory_returns_guide():
    service = SkillLearnerReviewLoopService()
    result = service.auto_scan(failure_memory=None, keyword="permission")
    assert result["scanned"] is False
    assert "未提供" in result["note"]


def test_auto_scan_imports_failures_and_detects_patterns():
    service = SkillLearnerReviewLoopService()
    counter = [0]

    class FakeFailure:
        def __init__(self, category):
            counter[0] += 1
            self.category = category
            self.failure_id = f"fail-{category}-{counter[0]}"
            self.description_cn = f"{category} 失败"
            self.occurred_at = "2026-01-01T00:00:00Z"

    class FakeMemory:
        def query_by_category(self, cat):
            return [FakeFailure(cat), FakeFailure(cat), FakeFailure(cat)]

    result = service.auto_scan(failure_memory=FakeMemory(), keyword="")
    assert result["scanned"] is True
    assert result["failures_imported"] == 12  # 4 categories x 3 unique failures
    assert result["patterns_found"] is True
    assert result["proposals_generated"] == 4  # 4 distinct categories


def test_auto_scan_generates_proposals_for_new_patterns():
    service = SkillLearnerReviewLoopService()
    counter = [0]

    class FakeFailure:
        def __init__(self, category):
            counter[0] += 1
            self.category = category
            self.failure_id = f"fail-{category}-{counter[0]}"
            self.description_cn = f"{category} 失败"
            self.occurred_at = "2026-01-01T00:00:00Z"

    class FakeMemory:
        def query_by_category(self, cat):
            return [FakeFailure(cat), FakeFailure(cat), FakeFailure(cat)]

    result = service.auto_scan(failure_memory=FakeMemory(), keyword="")
    assert result["proposals_generated"] == 4  # 4 distinct categories
    assert len(service.list_proposals()) == 4


def test_auto_scan_does_not_duplicate_proposals():
    service = SkillLearnerReviewLoopService()
    counter = [0]

    class FakeFailure:
        def __init__(self, category):
            counter[0] += 1
            self.category = category
            self.failure_id = f"fail-{category}-{counter[0]}"
            self.description_cn = f"{category} 失败"
            self.occurred_at = "2026-01-01T00:00:00Z"

    class FakeMemory:
        def query_by_category(self, cat):
            return [FakeFailure(cat), FakeFailure(cat), FakeFailure(cat)]

    # First scan
    result1 = service.auto_scan(failure_memory=FakeMemory(), keyword="")
    assert result1["proposals_generated"] == 4
    # Second scan - should not duplicate proposals
    result2 = service.auto_scan(failure_memory=FakeMemory(), keyword="")
    assert result2["proposals_generated"] == 0
    assert len(service.list_proposals()) == 4
