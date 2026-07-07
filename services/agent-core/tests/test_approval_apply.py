"""Tests for ApprovalApplyEngine."""
from pathlib import Path

import pytest

from bolt_core.approval_apply import ApprovalApplyEngine
from bolt_core.write_tool_proposal import (
    OP_MODIFY,
    RISK_LOW,
    STATUS_APPROVED,
    STATUS_PENDING,
    WriteProposalStore,
)


def make_store_with_approved(tmp_path: Path, **overrides):
    store = WriteProposalStore(project_dir=str(tmp_path))
    fields = {
        "tool_id": "write_file",
        "target_files": ["src/main.py"],
        "operation_type": OP_MODIFY,
        "before_summary": "前",
        "after_summary": "后",
        "diff_preview": "+new",
        "risk_level": RISK_LOW,
        "required_permissions": ["write"],
        "rollback_hint": "git checkout",
        "chinese_explanation": "测试提案",
    }
    fields.update(overrides)
    v = store.create(**fields)
    # Manually set status to approved (bypassing the store's normal flow for testing)
    prop = store.get(v.proposal.proposal_id)
    # Re-create with approved status
    store._proposals[prop.proposal_id] = prop.__class__(
        proposal_id=prop.proposal_id, tool_id=prop.tool_id,
        target_files=prop.target_files, operation_type=prop.operation_type,
        before_summary=prop.before_summary, after_summary=prop.after_summary,
        diff_preview=prop.diff_preview, risk_level=prop.risk_level,
        required_permissions=prop.required_permissions,
        rollback_hint=prop.rollback_hint,
        chinese_explanation=prop.chinese_explanation,
        git_head=prop.git_head, status=STATUS_APPROVED,
        created_at=prop.created_at,
    )
    return store, store.get(v.proposal.proposal_id)


class TestApprovalApply:
    def test_valid_approval_applies(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})
        assert result.success is True

    def test_no_proposal_fails(self, tmp_path):
        store, _ = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply("nope", {"actor": "human", "scope": "nope"})
        assert result.success is False
        assert "不存在" in result.reason

    def test_pending_proposal_fails(self, tmp_path):
        store = WriteProposalStore(project_dir=str(tmp_path))
        v = store.create(
            tool_id="write_file", target_files=["src/main.py"],
            operation_type=OP_MODIFY, before_summary="前", after_summary="后",
            diff_preview="+", risk_level=RISK_LOW,
            required_permissions=["write"], rollback_hint="r",
            chinese_explanation="测试",
        )
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply(v.proposal.proposal_id, {"actor": "human", "scope": v.proposal.proposal_id})
        assert result.success is False
        assert "批准" in result.reason

    def test_empty_approval_fails(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply(prop.proposal_id, {})
        assert result.success is False
        assert "批准记录" in result.reason

    def test_approved_true_bypass_fails(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply(prop.proposal_id, {"approved": True})
        assert result.success is False
        assert "绕过" in result.reason

    def test_agent_self_approve_fails(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply(prop.proposal_id, {"actor": "agent", "scope": prop.proposal_id})
        assert result.success is False
        assert "自我批准" in result.reason or "self" in result.reason.lower()

    def test_scope_mismatch_fails(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": "other_proposal"})
        assert result.success is False
        assert "不匹配" in result.reason

    def test_forged_approval_fails(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id, "forged": True})
        assert result.success is False
        assert "伪造" in result.reason

    def test_audit_record_on_success(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})
        assert result.success is True
        assert result.audit_record
        assert result.audit_record["proposal_id"] == prop.proposal_id

    def test_delete_operation_blocked(self, tmp_path):
        from bolt_core.write_tool_proposal import OP_DELETE, RISK_HIGH
        store, prop = make_store_with_approved(tmp_path, operation_type=OP_DELETE, risk_level=RISK_HIGH)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})
        assert result.success is False
        assert "删除" in result.reason
