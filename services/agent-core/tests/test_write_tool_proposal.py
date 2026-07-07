"""Tests for WriteProposalStore – create, query, cancel, stale check."""
from pathlib import Path

import pytest

from bolt_core.write_tool_proposal import (
    OP_CREATE,
    OP_DELETE,
    OP_MODIFY,
    RISK_HIGH,
    RISK_LOW,
    STATUS_CANCELLED,
    STATUS_PENDING,
    STATUS_STALE,
    WriteProposalStore,
)


# ── Helpers ──

def make_store(tmp_path: Path) -> WriteProposalStore:
    return WriteProposalStore(project_dir=str(tmp_path))


def make_proposal_fields(**overrides) -> dict:
    base = {
        "tool_id": "write_file",
        "target_files": ["src/main.py"],
        "operation_type": OP_MODIFY,
        "before_summary": "修改前",
        "after_summary": "修改后",
        "diff_preview": "- old\n+ new",
        "risk_level": RISK_LOW,
        "required_permissions": ["write"],
        "rollback_hint": "git checkout src/main.py",
        "chinese_explanation": "在 main.py 中添加一行日志输出",
    }
    base.update(overrides)
    return base


# ── Create proposal ──

class TestCreate:
    def test_creates_valid_proposal(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        assert v.valid is True
        assert v.proposal is not None
        assert v.proposal.status == STATUS_PENDING

    def test_generates_proposal_id(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        assert v.proposal.proposal_id.startswith("proposal_")

    def test_binds_git_head(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        assert v.proposal.git_head  # populated (or "unknown" if no git)

    def test_missing_tool_id_fails(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(tool_id=""))
        assert v.valid is False
        assert any("tool_id" in e for e in v.errors)

    def test_empty_target_files_fails(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(target_files=[]))
        assert v.valid is False

    def test_target_outside_project_fails(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(target_files=["../../etc/passwd"]))
        assert v.valid is False
        assert any("workspace" in e.lower() or "外" in e for e in v.errors)

    def test_target_secret_file_fails(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(target_files=[".env"]))
        assert v.valid is False
        assert any("secret" in e.lower() for e in v.errors)

    def test_target_claude_dir_fails(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(target_files=[".claude/config.txt"]))
        assert v.valid is False
        assert any(".claude" in e for e in v.errors)

    def test_delete_requires_high_risk(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(
            operation_type=OP_DELETE, risk_level=RISK_LOW,
            target_files=["src/old.py"],
        ))
        assert v.valid is False
        assert any("删除" in e for e in v.errors)


# ── Query proposals ──

class TestQuery:
    def test_get_existing(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        p = store.get(v.proposal.proposal_id)
        assert p is not None

    def test_get_missing(self, tmp_path):
        store = make_store(tmp_path)
        assert store.get("nope") is None

    def test_list_all(self, tmp_path):
        store = make_store(tmp_path)
        store.create(**make_proposal_fields())
        store.create(**make_proposal_fields(target_files=["src/other.py"]))
        assert len(store.list()) == 2

    def test_list_filter_by_status(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        store.cancel(v.proposal.proposal_id)
        assert len(store.list(status=STATUS_CANCELLED)) == 1


# ── Cancel proposal ──

class TestCancel:
    def test_cancel_pending(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        assert store.cancel(v.proposal.proposal_id) is True
        p = store.get(v.proposal.proposal_id)
        assert p.status == STATUS_CANCELLED

    def test_cancel_missing(self, tmp_path):
        store = make_store(tmp_path)
        assert store.cancel("nope") is False


# ── Stale check ──

class TestStale:
    def test_fresh_proposal_not_stale(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        result = store.check_stale(v.proposal.proposal_id)
        # Fresh proposal: current head == proposal head
        assert result["stale"] is False

    def test_missing_proposal_stale(self, tmp_path):
        store = make_store(tmp_path)
        result = store.check_stale("nope")
        assert result["stale"] is True


# ── Chinese fields ──

class TestChineseFields:
    def test_chinese_explanation_preserved(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(
            chinese_explanation="这是一条中文说明",
        ))
        assert "中文说明" in v.proposal.chinese_explanation

    def test_to_dict_has_labels(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields())
        d = v.proposal.to_dict()
        assert "operation_label" in d
        assert "risk_label" in d
        assert "status_label" in d


# ── Edge cases ──

class TestEdgeCases:
    def test_create_operation(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(
            operation_type=OP_CREATE, target_files=["src/new_file.py"],
        ))
        assert v.valid is True

    def test_invalid_operation_type(self, tmp_path):
        store = make_store(tmp_path)
        v = store.create(**make_proposal_fields(operation_type="explode"))
        assert v.valid is False
