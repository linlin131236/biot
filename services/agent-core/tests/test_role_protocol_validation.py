"""Tests for RoleProtocolService — validation, transitions, handoff, safety."""
import pytest

from bolt_core.role_protocol import RoleProtocolService


def test_explain_boundary_valid():
    svc = RoleProtocolService()
    result = svc.explain_boundary("builder")
    assert result["role_id"] == "builder"
    assert "can_do" in result
    assert "cannot_do" in result


def test_explain_boundary_invalid():
    svc = RoleProtocolService()
    result = svc.explain_boundary("unknown")
    assert "error" in result


# ── validate_transition ──────────────────────────────────────────────

def test_validate_transition_planner_to_builder():
    svc = RoleProtocolService()
    result = svc.validate_transition("planner", "builder")
    assert result.valid is True
    assert result.blocked is False


def test_validate_transition_builder_to_reviewer():
    svc = RoleProtocolService()
    result = svc.validate_transition("builder", "reviewer")
    assert result.valid is True
    assert "独立" in result.message_cn


def test_validate_transition_reviewer_to_builder():
    svc = RoleProtocolService()
    result = svc.validate_transition("reviewer", "builder")
    assert result.valid is True
    assert "不能自己实现" in result.message_cn


def test_validate_transition_planner_to_planner():
    svc = RoleProtocolService()
    result = svc.validate_transition("planner", "planner")
    assert result.valid is False
    assert result.blocked is True


def test_validate_transition_invalid_from():
    svc = RoleProtocolService()
    result = svc.validate_transition("unknown", "builder")
    assert result.valid is False
    assert result.blocked is True


def test_validate_transition_invalid_to():
    svc = RoleProtocolService()
    result = svc.validate_transition("planner", "unknown")
    assert result.valid is False
    assert result.blocked is True


# ── handoff ──────────────────────────────────────────────────────────

def test_get_handoff_format():
    svc = RoleProtocolService()
    fmt = svc.get_handoff_format()
    assert "fields" in fmt
    assert "required_fields" in fmt


def test_create_handoff_valid():
    svc = RoleProtocolService()
    hp = svc.create_handoff("planner", "builder", "task-001", "实现登录")
    assert hp.from_role == "planner"
    assert hp.to_role == "builder"
    assert hp.created_at


def test_create_handoff_invalid_transition():
    svc = RoleProtocolService()
    with pytest.raises(ValueError):
        svc.create_handoff("planner", "planner", "t", "s")


# ── assert_not_self_approval ─────────────────────────────────────────

def test_assert_not_self_approval_different():
    svc = RoleProtocolService()
    result = svc.assert_not_self_approval("ctx-builder", "ctx-reviewer")
    assert result.valid is True


def test_assert_not_self_approval_same():
    svc = RoleProtocolService()
    result = svc.assert_not_self_approval("ctx-same", "ctx-same")
    assert result.valid is False
    assert result.blocked is True
