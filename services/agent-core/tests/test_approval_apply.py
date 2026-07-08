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

    @pytest.mark.parametrize("actor", ["user", "father"])
    def test_ambiguous_actor_aliases_fail(self, tmp_path, actor):
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store)
        result = engine.apply(prop.proposal_id, {"actor": actor, "scope": prop.proposal_id})
        assert result.success is False
        assert "人工用户" in result.reason

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

    # ── Anti-corruption: multi-file diff safety ──

    def test_multi_target_mismatched_diff_fails(self, tmp_path):
        """A diff for src/a.py must not be applied to src/b.py when target_files has both."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
        (tmp_path / "src" / "b.py").write_text("print('b')\n", encoding="utf-8")

        # diff only modifies a.py
        diff_for_a = (
            "--- a/src/a.py\n"
            "+++ b/src/a.py\n"
            "@@ -1 +1 @@\n"
            "-print('a')\n"
            "+print('a_modified')\n"
        )
        store, prop = make_store_with_approved(
            tmp_path,
            target_files=["src/a.py", "src/b.py"],
            diff_preview=diff_for_a,
        )
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        # Must FAIL: diff has only a.py, but target_files includes b.py
        assert result.success is False
        assert "缺少对应 diff" in result.reason or "b.py" in result.reason

        # b.py must NOT be corrupted
        b_content = (tmp_path / "src" / "b.py").read_text(encoding="utf-8")
        assert "print('b')" in b_content, f"b.py was corrupted: {b_content}"

    def test_diff_extra_file_not_in_targets_fails(self, tmp_path):
        """Diff containing a file not in target_files must be rejected."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")

        diff_with_extra = (
            "--- a/src/a.py\n"
            "+++ b/src/a.py\n"
            "@@ -1 +1 @@\n"
            "-print('a')\n"
            "+print('a_new')\n"
            "--- a/src/secret.py\n"
            "+++ b/src/secret.py\n"
            "@@ -0,0 +1 @@\n"
            "+evil code\n"
        )
        store, prop = make_store_with_approved(
            tmp_path,
            target_files=["src/a.py"],
            diff_preview=diff_with_extra,
        )
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        # Must FAIL: diff references secret.py which is not in target_files
        assert result.success is False
        assert "非目标" in result.reason or "secret.py" in result.reason

    def test_two_file_diff_applies_correctly(self, tmp_path):
        """A proper two-file diff should apply to each file independently."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
        (tmp_path / "src" / "b.py").write_text("print('b')\n", encoding="utf-8")

        diff_two_files = (
            "--- a/src/a.py\n"
            "+++ b/src/a.py\n"
            "@@ -1 +1 @@\n"
            "-print('a')\n"
            "+print('a_new')\n"
            "--- a/src/b.py\n"
            "+++ b/src/b.py\n"
            "@@ -1 +1 @@\n"
            "-print('b')\n"
            "+print('b_new')\n"
        )
        store, prop = make_store_with_approved(
            tmp_path,
            target_files=["src/a.py", "src/b.py"],
            diff_preview=diff_two_files,
        )
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        assert result.success is True
        a_content = (tmp_path / "src" / "a.py").read_text(encoding="utf-8")
        b_content = (tmp_path / "src" / "b.py").read_text(encoding="utf-8")
        assert "print('a_new')" in a_content
        assert "print('b_new')" in b_content
        # Ensure no cross-contamination
        assert "print('a')" not in a_content
        assert "print('b')" not in b_content

    def test_apply_keeps_original_when_atomic_replace_fails(self, tmp_path, monkeypatch):
        """If final replace fails, approval apply must not leave a partially written target."""
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        target = tmp_path / "src" / "main.py"
        target.write_text("print('hello')\n", encoding="utf-8")

        def fail_replace(_src, _dst):
            raise OSError("replace failed")

        monkeypatch.setattr("os.replace", fail_replace)
        store, prop = make_store_with_approved(tmp_path)
        engine = ApprovalApplyEngine(store=store, project_dir=str(tmp_path))
        result = engine.apply(prop.proposal_id, {"actor": "human", "scope": prop.proposal_id})

        assert result.success is False
        assert "replace failed" in result.reason
        assert target.read_text(encoding="utf-8") == "print('hello')\n"
