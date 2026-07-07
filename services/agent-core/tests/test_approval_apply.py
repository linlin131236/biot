"""Tests for ApprovalApplyEngine – with real file write verification."""
from pathlib import Path

import pytest

from bolt_core.approval_apply import ApprovalApplyEngine
from bolt_core.write_tool_proposal import (
    OP_CREATE,
    OP_DELETE,
    OP_MODIFY,
    RISK_HIGH,
    RISK_LOW,
    STATUS_APPROVED,
    WriteProposalStore,
)


def make_store_with_approved(tmp_path: Path, **overrides):
    store = WriteProposalStore(project_dir=str(tmp_path))
    fields = {
        "tool_id": "write_file",
        "target_files": ["src/main.py"],
        "operation_type": OP_MODIFY,
        "before_summary": "print('hello')",
        "after_summary": "print('hello world')",
        "diff_preview": (
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1 +1 @@\n"
            "-print('hello')\n"
            "+print('hello world')\n"
        ),
        "risk_level": RISK_LOW,
        "required_permissions": ["write"],
        "rollback_hint": "git checkout src/main.py",
        "chinese_explanation": "修改 main.py 的打印内容",
    }
    fields.update(overrides)
    v = store.create(**fields)
    prop = store.get(v.proposal.proposal_id)
    # Set to approved
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


def make_modify_diff(old_line: str, new_line: str) -> str:
    return (
        f"--- a/src/main.py\n"
        f"+++ b/src/main.py\n"
        f"@@ -1 +1 @@\n"
        f"-{old_line}\n"
        f"+{new_line}\n"
    )


class TestApprovalApply:
    # ── Real file write ──

    def test_apply_modifies_file_content(self, tmp_path):
        """Apply should actually change the file content, not just mark_applied."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")

        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        assert result.success is True
        # Verify file was actually modified
        new_content = (tmp_path / "src" / "main.py").read_text(encoding="utf-8")
        assert "hello world" in new_content

    def test_apply_modify_multiline(self, tmp_path):
        """Multi-line diff should be applied correctly."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        original = "line1\nline2\nline3\n"
        (tmp_path / "src" / "main.py").write_text(original, encoding="utf-8")

        diff = (
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-line2\n"
            "+line2_modified\n"
            " line3\n"
        )
        store, prop = make_store_with_approved(tmp_path, diff_preview=diff)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        assert result.success is True
        new_content = (tmp_path / "src" / "main.py").read_text(encoding="utf-8")
        assert "line2_modified" in new_content
        assert "line2\n" not in new_content  # old line removed

    def test_apply_create_writes_new_file(self, tmp_path):
        """Create operation should write a new file."""
        diff = (
            "--- /dev/null\n"
            "+++ b/src/new_file.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+#!/usr/bin/env python\n"
            "+print('new file')\n"
        )
        store, prop = make_store_with_approved(
            tmp_path,
            operation_type=OP_CREATE,
            target_files=["src/new_file.py"],
            diff_preview=diff,
        )
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        assert result.success is True
        new_file = tmp_path / "src" / "new_file.py"
        assert new_file.exists()
        content = new_file.read_text(encoding="utf-8")
        assert "print('new file')" in content

    def test_apply_audit_records_files_changed(self, tmp_path):
        """Audit record should list the actual files changed, not just target_files."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")

        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        assert result.success is True
        assert result.audit_record["files_changed"] == ["src/main.py"]
        assert result.audit_record["result"] == "applied"

    # ── Existing security tests (updated) ──

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

    def test_delete_operation_blocked(self, tmp_path):
        store, prop = make_store_with_approved(tmp_path, operation_type=OP_DELETE, risk_level=RISK_HIGH)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})
        assert result.success is False
        assert "删除" in result.reason

    def test_modify_missing_file_fails(self, tmp_path):
        """Modifying a file that doesn't exist should fail (need existing file for modify)."""
        store, prop = make_store_with_approved(tmp_path)
        # Don't create src/main.py
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})
        assert result.success is False
        assert "不存在" in result.reason
