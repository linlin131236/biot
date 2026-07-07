"""Tests for RoleProtocolService."""
import pytest

from bolt_core.role_protocol import (
    RoleProtocolService,
    RoleProtocol,
    HandoffPackage,
    ValidationResult,
    _PLANNER,
    _BUILDER,
    _REVIEWER,
    _RESEARCHER,
    _SKILL_LEARNER,
)


# ── RoleProtocol dataclass ──────────────────────────────────────────────

def test_role_protocol_to_dict():
    r = _PLANNER
    d = r.to_dict()
    assert d["role_id"] == "planner"
    assert d["name_cn"] == "规划者"
    assert d["can_execute_code"] is False
    assert d["can_modify_files"] is False
    assert d["can_approve"] is False


def test_role_protocol_is_frozen():
    with pytest.raises(Exception):
        _PLANNER.role_id = "changed"  # type: ignore[misc]


# ── HandoffPackage ─────────────────────────────────────────────────────

def test_handoff_package_to_dict():
    hp = HandoffPackage(
        from_role="planner",
        to_role="builder",
        task_id="task-001",
        summary_cn="实现登录功能",
        evidence_refs=["docs/spec.md"],
        source_refs=["docs/decisions/001.md"],
        warnings=["注意安全"],
        created_at="2026-07-07T00:00:00Z",
    )
    d = hp.to_dict()
    assert d["from_role"] == "planner"
    assert d["to_role"] == "builder"
    assert d["summary_cn"] == "实现登录功能"


def test_handoff_package_is_frozen():
    hp = HandoffPackage(
        from_role="p", to_role="b", task_id="t", summary_cn="s",
        evidence_refs=[], source_refs=[], warnings=[], created_at="",
    )
    with pytest.raises(Exception):
        hp.summary_cn = "changed"  # type: ignore[misc]


# ── ValidationResult ───────────────────────────────────────────────────

def test_validation_result_ok():
    vr = ValidationResult(valid=True, message_cn="通过")
    d = vr.to_dict()
    assert d["valid"] is True
    assert d["message_cn"] == "通过"
    assert d["blocked"] is False


def test_validation_result_blocked():
    vr = ValidationResult(valid=False, message_cn="阻止", blocked=True)
    d = vr.to_dict()
    assert d["valid"] is False
    assert d["blocked"] is True


# ── Service: initialization ────────────────────────────────────────────

def test_service_creates():
    svc = RoleProtocolService()
    assert svc is not None


# ── Service: list_roles ────────────────────────────────────────────────

def test_list_roles_returns_5():
    svc = RoleProtocolService()
    roles = svc.list_roles()
    assert len(roles) == 5


def test_list_roles_canonical_order():
    svc = RoleProtocolService()
    roles = svc.list_roles()
    ids = [r.role_id for r in roles]
    assert ids == ["planner", "researcher", "builder", "reviewer", "skill_learner"]


def test_list_roles_all_have_chinese_names():
    svc = RoleProtocolService()
    for r in svc.list_roles():
        assert r.name_cn, f"{r.role_id} missing name_cn"
        assert r.description_cn, f"{r.role_id} missing description_cn"


# ── Service: get_role ─────────────────────────────────────────────────

def test_get_role_valid():
    svc = RoleProtocolService()
    r = svc.get_role("builder")
    assert r is not None
    assert r.role_id == "builder"
    assert r.can_execute_code is True
    assert r.can_modify_files is True
    assert r.can_approve is False


def test_get_role_invalid():
    svc = RoleProtocolService()
    r = svc.get_role("nonexistent")
    assert r is None


def test_get_role_planner():
    svc = RoleProtocolService()
    r = svc.get_role("planner")
    assert r is not None
    assert r.can_execute_code is False
    assert r.can_modify_files is False
    assert r.can_approve is False


# ── Service: role_ids ─────────────────────────────────────────────────

def test_role_ids():
    svc = RoleProtocolService()
    assert svc.role_ids() == ["planner", "researcher", "builder", "reviewer", "skill_learner"]


# ── Service: validate_output ──────────────────────────────────────────

def test_validate_output_missing_role():
    svc = RoleProtocolService()
    result = svc.validate_output("unknown", {"evidence_refs": ["a"]})
    assert result.valid is False
    assert result.blocked is True


def test_validate_output_missing_evidence():
    svc = RoleProtocolService()
    result = svc.validate_output("planner", {"task_breakdown": []})
    assert result.valid is False
    assert "evidence_refs" in " ".join(result.details).lower() or "source_refs" in " ".join(result.details).lower()


def test_validate_output_planner_with_evidence():
    svc = RoleProtocolService()
    result = svc.validate_output("planner", {
        "task_breakdown": [{"title": "t1"}],
        "risk_assessment": "low",
        "assignment": {"t1": "builder"},
        "source_refs": ["docs/spec.md"],
    })
    assert result.valid is True


def test_validate_output_builder_missing_tests():
    svc = RoleProtocolService()
    result = svc.validate_output("builder", {
        "code_changes": "git diff",
    })
    assert result.valid is False


def test_validate_output_builder_with_tests():
    svc = RoleProtocolService()
    result = svc.validate_output("builder", {
        "code_changes": "git diff",
        "tests": "all passed",
        "evidence_refs": ["test.log"],
        "source_refs": ["docs/spec.md"],
    })
    assert result.valid is True


def test_validate_output_reviewer_no_verdict():
    svc = RoleProtocolService()
    result = svc.validate_output("reviewer", {
        "findings": [],
        "evidence": ["code:line"],
        "tests_status": "passed",
        "residual_risks": [],
    })
    assert result.valid is False
    assert "verdict" in " ".join(result.details).lower()


def test_validate_output_reviewer_with_verdict():
    svc = RoleProtocolService()
    result = svc.validate_output("reviewer", {
        "findings": [{"severity": "P1", "desc": "bug"}],
        "evidence": ["file.py:10"],
        "tests_status": "passed",
        "residual_risks": [],
        "verdict": "approved",
        "source_refs": ["docs/review.md"],
    })
    assert result.valid is True


def test_validate_output_skill_learner_no_approval_flag():
    svc = RoleProtocolService()
    result = svc.validate_output("skill_learner", {
        "proposal_options": ["A", "B"],
        "evidence": ["failure pattern"],
        "source_refs": ["docs/failures.md"],
    })
    assert result.valid is False
    assert "father" in " ".join(result.details).lower() or "approval" in " ".join(result.details).lower()


def test_validate_output_skill_learner_with_approval():
    svc = RoleProtocolService()
    result = svc.validate_output("skill_learner", {
        "proposal_options": ["A", "B", "C"],
        "evidence": ["failure pattern"],
        "source_refs": ["docs/failures.md"],
        "target_type": "workflow_doc",
        "requires_father_approval": True,
    })
    assert result.valid is True


# ── Forbidden actions checks ──────────────────────────────────────────

def test_planner_cannot_execute_code():
    assert _PLANNER.can_execute_code is False
    assert _PLANNER.can_modify_files is False
    assert "编写或修改任何代码文件" in _PLANNER.forbidden_actions


def test_reviewer_cannot_modify_files():
    assert _REVIEWER.can_modify_files is False


def test_skill_learner_cannot_modify_code():
    assert _SKILL_LEARNER.can_modify_files is False
    assert "修改任何业务代码" in _SKILL_LEARNER.forbidden_actions


def test_builder_cannot_self_approve():
    assert _BUILDER.can_approve is False
    assert any("批准自己的工作" in f for f in _BUILDER.forbidden_actions)


def test_all_roles_have_forbidden_actions():
    svc = RoleProtocolService()
    for r in svc.list_roles():
        assert len(r.forbidden_actions) > 0, f"{r.role_id} has no forbidden_actions"


def test_all_roles_have_output_requirements():
    svc = RoleProtocolService()
    for r in svc.list_roles():
        assert len(r.output_requirements) > 0, f"{r.role_id} has no output_requirements"
