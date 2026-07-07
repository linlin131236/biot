"""Tests for ConflictResolutionService."""
from bolt_core.conflict_resolution import ConflictResolutionService, ConflictType, ConflictSeverity


def test_detect_review_conflict():
    svc = ConflictResolutionService()
    c = svc.detect("review_conflict", "Builder passed vs Reviewer blocked", "builder", "reviewer", ["docs/review.md"])
    assert c.conflict_type == ConflictType.REVIEW
    assert c.severity == ConflictSeverity.HIGH
    assert not c.resolved


def test_detect_safety_conflict():
    svc = ConflictResolutionService()
    c = svc.detect("safety_conflict", "PermissionGate bypass attempt", "builder", "reviewer")
    assert c.severity == ConflictSeverity.CRITICAL
    assert c.requires_human is True


def test_detect_evidence_conflict():
    svc = ConflictResolutionService()
    c = svc.detect("evidence_conflict", "Researcher source conflicts with Planner", "researcher", "planner")
    assert c.conflict_type == ConflictType.EVIDENCE


def test_list_conflicts():
    svc = ConflictResolutionService()
    svc.detect("review_conflict", "d", "a", "b")
    svc.detect("safety_conflict", "d", "a", "b")
    assert len(svc.list_conflicts()) == 2


def test_resolve_conflict():
    svc = ConflictResolutionService()
    c = svc.detect("evidence_conflict", "d", "a", "b")
    resolved = svc.resolve(c.conflict_id, "A", "采纳A方案")
    assert resolved is not None
    assert resolved.resolved


def test_resolution_options_generated():
    svc = ConflictResolutionService()
    c = svc.detect("review_conflict", "d", "a", "b")
    assert len(c.resolution_options) >= 2
