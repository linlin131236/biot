"""Tests for ToolManifest and ToolManifestValidator."""
import pytest

from bolt_core.tool_manifest import (
    SIDE_EFFECT_DANGEROUS,
    SIDE_EFFECT_READ_ONLY,
    SIDE_EFFECT_WRITE,
    ManifestValidationResult,
    ToolManifest,
    ToolManifestValidator,
)
from bolt_core.tool_registry import (
    CATEGORY_DANGEROUS,
    CATEGORY_READ_ONLY,
    CATEGORY_WRITE,
    PERM_DANGEROUS,
    PERM_NONE,
    PERM_WRITE,
    ToolDef,
    ToolRegistry,
)


# ── Helpers ──

def make_valid_manifest(**overrides) -> dict:
    """Return a minimal valid manifest dict."""
    base = {
        "tool_id": "test_tool",
        "version": "1.0.0",
        "display_name": "测试工具",
        "capability_summary": "用于测试的工具能力声明",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
        "output_schema": {"type": "string"},
        "side_effect_level": SIDE_EFFECT_READ_ONLY,
        "permission_contract": {
            "required_level": PERM_NONE,
            "human_approval_required": False,
            "approval_scope": "test_tool",
        },
        "audit_requirements": {
            "log_calls": True,
            "log_results": True,
            "evidence_required": False,
        },
        "rollback_support": False,
    }
    base.update(overrides)
    return base


def make_registry_with_tool(tool_id="test_tool", **overrides) -> ToolRegistry:
    r = ToolRegistry()
    defaults = {
        "tool_id": tool_id,
        "display_name": "测试工具",
        "category": CATEGORY_READ_ONLY,
        "description": "测试工具描述",
        "permission_required": PERM_NONE,
        "allow_auto_run": True,
        "risk_level": "low",
    }
    defaults.update(overrides)
    r.register(ToolDef(**defaults))
    return r


# ── ToolManifest dataclass ──

class TestToolManifest:
    def test_valid_manifest(self):
        m = ToolManifest(
            tool_id="test", version="1.0.0", display_name="T",
            capability_summary="CS", side_effect_level=SIDE_EFFECT_READ_ONLY,
        )
        assert m.tool_id == "test"
        assert m.version == "1.0.0"

    def test_empty_tool_id_raises(self):
        with pytest.raises(ValueError, match="tool_id 不能为空"):
            ToolManifest(tool_id="", version="1.0", display_name="T", capability_summary="CS")

    def test_empty_version_raises(self):
        with pytest.raises(ValueError, match="version 不能为空"):
            ToolManifest(tool_id="t", version="", display_name="T", capability_summary="CS")

    def test_invalid_side_effect_raises(self):
        with pytest.raises(ValueError, match="未知副作用等级"):
            ToolManifest(tool_id="t", version="1.0", display_name="T",
                        capability_summary="CS", side_effect_level="invalid")

    def test_to_dict(self):
        m = ToolManifest(tool_id="t", version="1.0", display_name="测试",
                        capability_summary="能力", side_effect_level=SIDE_EFFECT_READ_ONLY)
        d = m.to_dict()
        assert d["tool_id"] == "t"
        assert d["side_effect_label"] == "只读"


# ── Structural validation ──

class TestValidateStructural:
    def test_valid_manifest_passes(self):
        m = make_valid_manifest()
        r = ToolManifestValidator.validate(m)
        assert r.valid is True
        assert len(r.errors) == 0

    def test_missing_tool_id_fails(self):
        m = make_valid_manifest()
        del m["tool_id"]
        r = ToolManifestValidator.validate(m)
        assert r.valid is False
        assert any("tool_id" in e for e in r.errors)

    def test_missing_version_fails(self):
        m = make_valid_manifest()
        del m["version"]
        r = ToolManifestValidator.validate(m)
        assert r.valid is False
        assert any("version" in e for e in r.errors)

    def test_missing_capability_summary_fails(self):
        m = make_valid_manifest()
        del m["capability_summary"]
        r = ToolManifestValidator.validate(m)
        assert r.valid is False
        assert any("capability_summary" in e for e in r.errors)

    def test_missing_permission_contract_fails(self):
        m = make_valid_manifest()
        m["permission_contract"] = {}
        r = ToolManifestValidator.validate(m)
        assert r.valid is False
        assert any("permission_contract" in e for e in r.errors)

    def test_invalid_version_format(self):
        m = make_valid_manifest(version="abc")
        r = ToolManifestValidator.validate(m)
        assert not r.valid
        assert any("version" in e for e in r.errors)

    def test_invalid_side_effect_level(self):
        m = make_valid_manifest(side_effect_level="super_dangerous")
        r = ToolManifestValidator.validate(m)
        assert not r.valid

    def test_dangerous_missing_human_approval_fails(self):
        m = make_valid_manifest(
            side_effect_level=SIDE_EFFECT_DANGEROUS,
            permission_contract={"required_level": PERM_DANGEROUS, "human_approval_required": False},
        )
        r = ToolManifestValidator.validate(m)
        assert not r.valid
        assert any("human_approval_required" in e for e in r.errors)

    def test_dangerous_missing_approval_scope_fails(self):
        m = make_valid_manifest(
            side_effect_level=SIDE_EFFECT_DANGEROUS,
            permission_contract={"required_level": PERM_DANGEROUS, "human_approval_required": True},
        )
        r = ToolManifestValidator.validate(m)
        assert not r.valid
        assert any("approval_scope" in e for e in r.errors)

    def test_dangerous_with_human_approval_passes(self):
        m = make_valid_manifest(
            side_effect_level=SIDE_EFFECT_DANGEROUS,
            permission_contract={
                "required_level": PERM_DANGEROUS,
                "human_approval_required": True,
                "approval_scope": "test_tool",
            },
        )
        r = ToolManifestValidator.validate(m)
        assert r.valid is True


# ── Registry cross-validation ──

class TestValidateAgainstRegistry:
    def test_matching_registry_passes(self):
        m = make_valid_manifest()
        reg = make_registry_with_tool(category=CATEGORY_READ_ONLY, permission_required=PERM_NONE)
        r = ToolManifestValidator.validate_against_registry(m, reg)
        assert r.valid is True

    def test_tool_not_in_registry_fails(self):
        m = make_valid_manifest(tool_id="not_registered")
        reg = make_registry_with_tool()
        r = ToolManifestValidator.validate_against_registry(m, reg)
        assert not r.valid
        assert any("未在注册表中注册" in e for e in r.errors)

    def test_side_effect_mismatch_fails(self):
        m = make_valid_manifest(side_effect_level=SIDE_EFFECT_WRITE)
        reg = make_registry_with_tool(category=CATEGORY_READ_ONLY)
        r = ToolManifestValidator.validate_against_registry(m, reg)
        assert not r.valid
        assert any("不匹配" in e for e in r.errors)

    def test_permission_mismatch_fails(self):
        m = make_valid_manifest(
            permission_contract={"required_level": PERM_DANGEROUS, "human_approval_required": False},
        )
        reg = make_registry_with_tool(permission_required=PERM_NONE)
        r = ToolManifestValidator.validate_against_registry(m, reg)
        assert not r.valid
        assert any("不一致" in e for e in r.errors)

    def test_write_permission_needs_human_approval(self):
        m = make_valid_manifest(
            side_effect_level=SIDE_EFFECT_WRITE,
            permission_contract={"required_level": PERM_WRITE, "human_approval_required": False},
        )
        reg = make_registry_with_tool(category=CATEGORY_WRITE, permission_required=PERM_WRITE)
        r = ToolManifestValidator.validate_against_registry(m, reg)
        assert not r.valid
        assert any("人工批准" in e for e in r.errors)

    def test_dangerous_with_matching_registry_passes(self):
        m = make_valid_manifest(
            side_effect_level=SIDE_EFFECT_DANGEROUS,
            permission_contract={
                "required_level": PERM_DANGEROUS,
                "human_approval_required": True,
                "approval_scope": "test_tool",
            },
        )
        reg = make_registry_with_tool(
            category=CATEGORY_DANGEROUS, permission_required=PERM_DANGEROUS,
            allow_auto_run=False, risk_level="high",
        )
        r = ToolManifestValidator.validate_against_registry(m, reg)
        assert r.valid is True


# ── ManifestValidationResult ──

class TestValidationResult:
    def test_to_dict(self):
        r = ManifestValidationResult(valid=True, errors=[], warnings=["建议添加描述"])
        d = r.to_dict()
        assert d["valid"] is True
        assert d["error_count"] == 0
        assert d["warning_count"] == 1
