"""Tool Manifest. Describes what a tool can do, what permissions it needs,
and what side effects it produces. Does NOT execute tools."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from bolt_core.tool_registry import (
    CATEGORY_DANGEROUS,
    CATEGORY_READ_ONLY,
    CATEGORY_SIDE_EFFECT,
    CATEGORY_WRITE,
    PERM_DANGEROUS,
    PERM_EXECUTE,
    PERM_NONE,
    PERM_READ,
    PERM_WRITE,
    ToolRegistry,
)

# ── Side effect levels ──
SIDE_EFFECT_NONE = "none"
SIDE_EFFECT_READ_ONLY = "read_only"
SIDE_EFFECT_SIDE_EFFECT = "side_effect"
SIDE_EFFECT_WRITE = "write"
SIDE_EFFECT_DANGEROUS = "dangerous"

SIDE_EFFECT_LEVELS = {
    SIDE_EFFECT_NONE, SIDE_EFFECT_READ_ONLY, SIDE_EFFECT_SIDE_EFFECT,
    SIDE_EFFECT_WRITE, SIDE_EFFECT_DANGEROUS,
}

SIDE_EFFECT_LABELS: dict[str, str] = {
    SIDE_EFFECT_NONE: "无副作用",
    SIDE_EFFECT_READ_ONLY: "只读",
    SIDE_EFFECT_SIDE_EFFECT: "有副作用",
    SIDE_EFFECT_WRITE: "写入",
    SIDE_EFFECT_DANGEROUS: "危险",
}

# ── Required manifest fields ──
_REQUIRED_FIELDS = [
    "tool_id", "version", "display_name", "capability_summary",
    "input_schema", "side_effect_level", "permission_contract",
]

# ── Permission levels requiring human approval ──
_HUMAN_APPROVAL_PERMS = {PERM_WRITE, PERM_EXECUTE, PERM_DANGEROUS}


@dataclass(frozen=True)
class ManifestValidationResult:
    """Result of manifest validation. Contains all errors found."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


@dataclass(frozen=True)
class ToolManifest:
    """Immutable tool manifest. Describes capabilities, permissions, and audit needs."""
    tool_id: str
    version: str
    display_name: str
    capability_summary: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    side_effect_level: str = SIDE_EFFECT_READ_ONLY
    permission_contract: dict = field(default_factory=dict)
    audit_requirements: dict = field(default_factory=dict)
    rollback_support: bool = False

    def __post_init__(self):
        if not self.tool_id or not isinstance(self.tool_id, str):
            raise ValueError("tool_id 不能为空")
        if not self.version or not isinstance(self.version, str):
            raise ValueError("version 不能为空")
        if self.side_effect_level not in SIDE_EFFECT_LEVELS:
            raise ValueError(f"未知副作用等级: {self.side_effect_level}")

    def to_dict(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "version": self.version,
            "display_name": self.display_name,
            "capability_summary": self.capability_summary,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "side_effect_level": self.side_effect_level,
            "side_effect_label": SIDE_EFFECT_LABELS.get(self.side_effect_level, "未知"),
            "permission_contract": self.permission_contract,
            "audit_requirements": self.audit_requirements,
            "rollback_support": self.rollback_support,
        }


class ToolManifestValidator:
    """Validates tool manifests. Does NOT execute tools."""

    @staticmethod
    def validate(manifest_data: dict) -> ManifestValidationResult:
        """Validate a manifest dict against structural requirements."""
        errors: list[str] = []
        warnings: list[str] = []

        # ── Check required fields ──
        for field in _REQUIRED_FIELDS:
            if field not in manifest_data or not manifest_data[field]:
                errors.append(f"缺少必填字段: {field}")

        tool_id = str(manifest_data.get("tool_id", ""))
        version = str(manifest_data.get("version", ""))

        # ── Validate tool_id ──
        if tool_id and not tool_id.strip():
            errors.append("tool_id 不能为空白")

        # ── Validate version format (semver-like) ──
        if version:
            parts = version.split(".")
            if len(parts) < 2 or not all(p.isdigit() for p in parts):
                errors.append(f"version 格式无效: '{version}'，应为语义版本如 '1.0.0'")

        # ── Validate side_effect_level ──
        side_effect = str(manifest_data.get("side_effect_level", ""))
        if side_effect and side_effect not in SIDE_EFFECT_LEVELS:
            errors.append(f"未知副作用等级: {side_effect}，合法值: {SIDE_EFFECT_LEVELS}")

        # ── Validate permission_contract ──
        perm_contract = manifest_data.get("permission_contract", {})
        if isinstance(perm_contract, dict):
            if not perm_contract:
                errors.append("缺少 permission_contract，必须声明权限契约")
            else:
                req_level = perm_contract.get("required_level", "")
                if req_level and req_level not in [PERM_NONE, PERM_READ, PERM_WRITE, PERM_EXECUTE, PERM_DANGEROUS]:
                    errors.append(f"permission_contract.required_level 无效: {req_level}")
        else:
            errors.append("permission_contract 必须是一个对象")

        # ── Dangerous tools must declare human approval ──
        is_dangerous = side_effect == SIDE_EFFECT_DANGEROUS
        if is_dangerous:
            if isinstance(perm_contract, dict):
                if not perm_contract.get("human_approval_required", False):
                    errors.append("危险工具必须声明 human_approval_required = true")
                if not perm_contract.get("approval_scope"):
                    errors.append("危险工具必须声明 approval_scope（批准范围）")

        # ── Validate input_schema ──
        input_schema = manifest_data.get("input_schema", {})
        if isinstance(input_schema, dict) and input_schema:
            if "type" not in input_schema:
                warnings.append("input_schema 建议包含 'type' 字段（如 'object'）")

        # ── Audit requirements check ──
        audit = manifest_data.get("audit_requirements", {})
        if isinstance(audit, dict):
            if is_dangerous and not audit.get("evidence_required", False):
                warnings.append("危险工具建议开启 audit_requirements.evidence_required")

        valid = len(errors) == 0
        return ManifestValidationResult(valid=valid, errors=errors, warnings=warnings)

    @staticmethod
    def validate_against_registry(
        manifest_data: dict, registry: ToolRegistry
    ) -> ManifestValidationResult:
        """Validate manifest against the tool registry for consistency."""
        errors: list[str] = []
        warnings: list[str] = []

        tool_id = str(manifest_data.get("tool_id", ""))
        if not tool_id:
            errors.append("tool_id 缺失，无法与注册表对照")
            return ManifestValidationResult(valid=False, errors=errors, warnings=warnings)

        tool_def = registry.get(tool_id)
        if tool_def is None:
            errors.append(f"工具 '{tool_id}' 未在注册表中注册，请先注册工具")
            return ManifestValidationResult(valid=False, errors=errors, warnings=warnings)

        # ── Check side_effect vs registry category ──
        side_effect = str(manifest_data.get("side_effect_level", ""))
        reg_category = tool_def.category

        # Mapping: registry category → expected side_effect_level
        _category_to_side_effect = {
            CATEGORY_READ_ONLY: SIDE_EFFECT_READ_ONLY,
            CATEGORY_SIDE_EFFECT: SIDE_EFFECT_SIDE_EFFECT,
            CATEGORY_WRITE: SIDE_EFFECT_WRITE,
            CATEGORY_DANGEROUS: SIDE_EFFECT_DANGEROUS,
        }
        expected_se = _category_to_side_effect.get(reg_category)
        if expected_se and side_effect and side_effect != expected_se:
            errors.append(
                f"副作用等级 '{side_effect}' 与注册表类别 '{reg_category}' 不匹配"
                f"（期望 '{expected_se}'）"
            )

        # ── Check permission_contract vs registry permission ──
        perm_contract = manifest_data.get("permission_contract", {})
        if isinstance(perm_contract, dict):
            req_level = perm_contract.get("required_level", "")
            reg_perm = tool_def.permission_required
            if req_level and reg_perm:
                if req_level != reg_perm:
                    errors.append(
                        f"permission_contract.required_level '{req_level}' 与注册表"
                        f" permission_required '{reg_perm}' 不一致"
                    )

            # Permission levels requiring human approval must have it declared
            if req_level in _HUMAN_APPROVAL_PERMS:
                if not perm_contract.get("human_approval_required", False):
                    errors.append(
                        f"权限等级 '{req_level}' 需要人工批准，但 manifest 中"
                        f" human_approval_required 未设为 true"
                    )

        valid = len(errors) == 0
        return ManifestValidationResult(valid=valid, errors=errors, warnings=warnings)
