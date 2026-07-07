"""Tests for PatchProposalEngine – create, validate, preview, budget, security."""
from pathlib import Path

import pytest

from bolt_core.patch_proposal import (
    OP_CREATE,
    OP_DELETE,
    OP_MODIFY,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    PatchProposalEngine,
)


# ── Helpers ──

def make_engine(tmp_path: Path) -> PatchProposalEngine:
    return PatchProposalEngine(project_dir=str(tmp_path))


def make_patch_fields(**overrides) -> dict:
    base = {
        "description": "添加日志到 main.py",
        "files": [{
            "file_path": "src/main.py",
            "operation": OP_MODIFY,
            "hunks": [{
                "old_start": 1, "old_count": 1,
                "new_start": 1, "new_count": 2,
                "lines": [" print('hello')", "+ print('world')"],
            }],
        }],
        "unified_diff": "--- a/src/main.py\n+++ b/src/main.py\n@@ -1 +1,2 @@\n print('hello')\n+print('world')",
        "risk_level": RISK_LOW,
    }
    base.update(overrides)
    return base


# ── Create ──

class TestCreate:
    def test_creates_valid_patch(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields())
        assert v.valid is True
        assert v.patch is not None
        assert v.patch.total_files == 1

    def test_generates_patch_id(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields())
        assert v.patch.patch_id.startswith("patch_")

    def test_empty_description_fails(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(description=""))
        assert v.valid is False

    def test_empty_files_fails(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(files=[]))
        assert v.valid is False

    def test_invalid_file_path_fails(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(files=[{"file_path": "", "operation": OP_MODIFY}]))
        assert v.valid is False

    def test_outside_workspace_fails(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(files=[{"file_path": "../../etc/passwd", "operation": OP_MODIFY}]))
        assert v.valid is False

    def test_secret_file_fails(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(files=[{"file_path": ".env", "operation": OP_MODIFY}]))
        assert v.valid is False

    def test_claude_dir_fails(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(files=[{"file_path": ".claude/config.txt", "operation": OP_MODIFY}]))
        assert v.valid is False

    def test_delete_auto_raises_risk(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(files=[{"file_path": "src/old.py", "operation": OP_DELETE}]))
        assert v.valid is True
        assert v.patch.risk_level == RISK_HIGH
        assert any("删除" in w for w in v.warnings)

    def test_many_files_raises_risk(self, tmp_path):
        engine = make_engine(tmp_path)
        files = [{"file_path": f"src/file_{i}.py", "operation": OP_MODIFY} for i in range(11)]
        v = engine.create(**make_patch_fields(files=files, risk_level=RISK_LOW))
        assert v.valid is True
        assert v.patch.risk_level == RISK_MEDIUM

    def test_multi_file_patch(self, tmp_path):
        engine = make_engine(tmp_path)
        files = [
            {"file_path": "src/a.py", "operation": OP_MODIFY},
            {"file_path": "src/b.py", "operation": OP_CREATE},
        ]
        v = engine.create(**make_patch_fields(files=files))
        assert v.valid is True
        assert v.patch.total_files == 2


# ── Budget ──

class TestBudget:
    def test_too_many_files_fails(self, tmp_path):
        engine = make_engine(tmp_path)
        files = [{"file_path": f"src/f{i}.py", "operation": OP_MODIFY} for i in range(25)]
        v = engine.create(**make_patch_fields(files=files))
        assert v.valid is False
        assert any("文件数" in e for e in v.errors)


# ── Query ──

class TestQuery:
    def test_get_existing(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields())
        p = engine.get(v.patch.patch_id)
        assert p is not None

    def test_get_missing(self, tmp_path):
        engine = make_engine(tmp_path)
        assert engine.get("nope") is None

    def test_list_returns_all(self, tmp_path):
        engine = make_engine(tmp_path)
        engine.create(**make_patch_fields())
        engine.create(**make_patch_fields(files=[{"file_path": "src/other.py", "operation": OP_MODIFY}]))
        assert len(engine.list()) == 2


# ── Preview ──

class TestPreview:
    def test_preview_shows_diff(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields())
        preview = engine.preview(v.patch.patch_id)
        assert "unified_diff" in preview
        assert "disclaimer" in preview

    def test_preview_missing(self, tmp_path):
        engine = make_engine(tmp_path)
        preview = engine.preview("nope")
        assert "error" in preview


# ── Audit ──

class TestAudit:
    def test_audit_hash_generated(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields())
        assert v.patch.audit_hash

    def test_to_dict_has_all_fields(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields())
        d = v.patch.to_dict()
        for key in ("patch_id", "description", "files", "unified_diff", "risk_level",
                     "risk_label", "status", "total_lines", "total_files", "audit_hash"):
            assert key in d, f"Missing key: {key}"


# ── Invalid operation ──

class TestInvalidOperation:
    def test_invalid_operation_rejected(self, tmp_path):
        engine = make_engine(tmp_path)
        v = engine.create(**make_patch_fields(files=[{"file_path": "src/x.py", "operation": "explode"}]))
        assert v.valid is False
