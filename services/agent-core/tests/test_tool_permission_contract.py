"""Tests for PermissionContractEngine – evaluate and verify."""
import pytest

from bolt_core.tool_permission_contract import (
    DECISION_ALLOWED,
    DECISION_DENIED,
    DECISION_NEEDS_APPROVAL,
    LEVEL_DANGEROUS,
    LEVEL_READ,
    LEVEL_WRITE,
    ApprovalVerification,
    PermissionContractEngine,
    PermissionDecision,
)
from bolt_core.tool_registry import (
    CATEGORY_DANGEROUS,
    CATEGORY_READ_ONLY,
    CATEGORY_WRITE,
    PERM_DANGEROUS,
    PERM_NONE,
    PERM_READ,
    PERM_WRITE,
    ToolDef,
    ToolRegistry,
)


# ── Helpers ──

def make_registry(**tools) -> ToolRegistry:
    """Create registry with given tools. Each kwarg = tool_id → category."""
    r = ToolRegistry()
    for tool_id, category in tools.items():
        perm_map = {
            CATEGORY_READ_ONLY: PERM_READ,
            CATEGORY_WRITE: PERM_WRITE,
            CATEGORY_DANGEROUS: PERM_DANGEROUS,
        }
        r.register(ToolDef(
            tool_id=tool_id, display_name=f"工具{tool_id}",
            category=category, description=f"描述_{tool_id}",
            permission_required=perm_map.get(category, PERM_NONE),
            allow_auto_run=(category == CATEGORY_READ_ONLY),
            risk_level="high" if category == CATEGORY_DANGEROUS else "low",
        ))
    return r


# ── PermissionDecision ──

class TestPermissionDecision:
    def test_to_dict(self):
        d = PermissionDecision(
            tool_id="t", decision=DECISION_ALLOWED, reason="OK",
            required_level=LEVEL_READ,
        )
        out = d.to_dict()
        assert out["tool_id"] == "t"
        assert out["decision"] == DECISION_ALLOWED
        assert "decision_label" in out

    def test_denied_decision(self):
        d = PermissionDecision(tool_id="t", decision=DECISION_DENIED, reason="未知")
        assert d.decision == DECISION_DENIED
        assert d.human_approval_required is False


# ── Evaluate: unknown / no registry ──

class TestEvaluateUnknown:
    def test_unknown_tool_denied(self):
        d = PermissionContractEngine.evaluate("no_such_tool")
        assert d.decision == DECISION_DENIED
        assert "未注册" in d.reason

    def test_empty_registry_denied(self):
        r = ToolRegistry()
        d = PermissionContractEngine.evaluate("x", registry=r)
        assert d.decision == DECISION_DENIED

    def test_none_registry_denied(self):
        d = PermissionContractEngine.evaluate("x", registry=None)
        assert d.decision == DECISION_DENIED


# ── Evaluate: read-only tools ──

class TestEvaluateReadOnly:
    def test_read_only_allowed(self):
        r = make_registry(read_file=CATEGORY_READ_ONLY)
        d = PermissionContractEngine.evaluate("read_file", registry=r)
        assert d.decision == DECISION_ALLOWED
        assert d.human_approval_required is False

    def test_read_tool_no_approval_needed(self):
        r = make_registry(list_files=CATEGORY_READ_ONLY)
        d = PermissionContractEngine.evaluate("list_files", registry=r)
        assert d.human_approval_required is False
        assert d.required_level == LEVEL_READ


# ── Evaluate: write tools ──

class TestEvaluateWrite:
    def test_write_tool_needs_approval(self):
        r = make_registry(write_file=CATEGORY_WRITE)
        d = PermissionContractEngine.evaluate("write_file", registry=r)
        assert d.decision == DECISION_NEEDS_APPROVAL
        assert d.human_approval_required is True
        assert d.required_approval_by == "human"

    def test_write_tool_required_level(self):
        r = make_registry(edit_file=CATEGORY_WRITE)
        d = PermissionContractEngine.evaluate("edit_file", registry=r)
        assert d.required_level == LEVEL_WRITE


# ── Evaluate: dangerous tools ──

class TestEvaluateDangerous:
    def test_dangerous_tool_needs_approval(self):
        r = make_registry(shell_exec=CATEGORY_DANGEROUS)
        d = PermissionContractEngine.evaluate("shell_exec", registry=r)
        assert d.decision == DECISION_NEEDS_APPROVAL
        assert d.required_level == LEVEL_DANGEROUS

    def test_dangerous_op_always_needs_approval(self):
        """Even without a registry, push/release/tag/delete are always dangerous."""
        for op in ("push", "release", "tag", "delete"):
            d = PermissionContractEngine.evaluate("any_tool", operation=op)
            assert d.decision == DECISION_NEEDS_APPROVAL, f"op={op}"
            assert d.required_level == LEVEL_DANGEROUS, f"op={op}"


# ── Evaluate: always dangerous operations ──

class TestAlwaysDangerousOps:
    def test_force_push_dangerous(self):
        d = PermissionContractEngine.evaluate("git", operation="force_push")
        assert d.decision == DECISION_NEEDS_APPROVAL
        assert "永久危险" in d.reason

    def test_credential_read_dangerous(self):
        d = PermissionContractEngine.evaluate("env_reader", operation="credential_read")
        assert d.decision == DECISION_NEEDS_APPROVAL

    def test_permission_bypass_blocked(self):
        d = PermissionContractEngine.evaluate("gate", operation="permission_bypass")
        assert d.decision == DECISION_NEEDS_APPROVAL


# ── Verify approval ──

class TestVerifyApproval:
    def test_valid_human_approval(self):
        decision = PermissionDecision(
            tool_id="t", decision=DECISION_NEEDS_APPROVAL, reason="需要批准",
            required_level=LEVEL_WRITE, human_approval_required=True,
            required_approval_by="human",
        )
        approval = {"actor": "human", "scope": "t"}
        v = PermissionContractEngine.verify_approval(decision, approval)
        assert v.valid is True

    def test_empty_approval_fails(self):
        decision = PermissionDecision(tool_id="t", decision=DECISION_NEEDS_APPROVAL, reason="r")
        v = PermissionContractEngine.verify_approval(decision, {})
        assert v.valid is False
        assert "缺少批准记录" in v.reason or "批准记录为空" in v.reason

    def test_approved_true_bypass_rejected(self):
        decision = PermissionDecision(tool_id="t", decision=DECISION_NEEDS_APPROVAL, reason="r")
        approval = {"approved": True}
        v = PermissionContractEngine.verify_approval(decision, approval)
        assert v.valid is False
        assert "绕过" in v.reason

    def test_agent_self_approval_rejected(self):
        decision = PermissionDecision(tool_id="t", decision=DECISION_NEEDS_APPROVAL, reason="r")
        approval = {"actor": "agent", "scope": "t"}
        v = PermissionContractEngine.verify_approval(decision, approval)
        assert v.valid is False
        assert "自我批准" in v.reason or "self-approve" in v.reason

    def test_scope_mismatch_rejected(self):
        decision = PermissionDecision(tool_id="edit_file", decision=DECISION_NEEDS_APPROVAL, reason="r")
        approval = {"actor": "human", "scope": "other_tool"}
        v = PermissionContractEngine.verify_approval(decision, approval)
        assert v.valid is False
        assert "不匹配" in v.reason

    def test_forged_approval_rejected(self):
        decision = PermissionDecision(tool_id="t", decision=DECISION_NEEDS_APPROVAL, reason="r")
        approval = {"actor": "human", "scope": "t", "forged": True}
        v = PermissionContractEngine.verify_approval(decision, approval)
        assert v.valid is False
        assert "伪造" in v.reason

    def test_auto_generated_rejected(self):
        decision = PermissionDecision(tool_id="t", decision=DECISION_NEEDS_APPROVAL, reason="r")
        approval = {"actor": "human", "scope": "t", "auto_generated": True}
        v = PermissionContractEngine.verify_approval(decision, approval)
        assert v.valid is False


# ── Dangerous ops list ──

class TestDangerousOpsList:
    def test_list_contains_core_ops(self):
        ops = PermissionContractEngine.list_dangerous_ops()
        always = ops["always_dangerous_ops"]
        assert "push" in always
        assert "delete" in always
        assert "release" in always
        assert "tag" in always

    def test_list_has_disclaimer(self):
        ops = PermissionContractEngine.list_dangerous_ops()
        assert "disclaimer" in ops


# ── ApprovalVerification ──

class TestApprovalVerification:
    def test_to_dict(self):
        v = ApprovalVerification(valid=True, reason="通过", checks=[
            {"check": "actor", "passed": True, "detail": "human"},
        ])
        d = v.to_dict()
        assert d["valid"] is True
        assert len(d["checks"]) == 1
