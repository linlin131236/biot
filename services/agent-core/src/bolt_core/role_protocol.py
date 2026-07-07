"""Multi-Agent Role Protocol Service. Read-only; validates role boundaries,
outputs, and transitions without auto-executing anything.

Role definitions live in role_protocol_models.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bolt_core.role_protocol_models import (
    RoleProtocol, HandoffPackage, ValidationResult,
    _ROLES, _ROLE_ORDER,
    _PLANNER, _RESEARCHER, _BUILDER, _REVIEWER, _SKILL_LEARNER,
    _BUILDER_SELF_APPROVAL_MESSAGE, _REVIEWER_SELF_IMPLEMENT_MESSAGE,
)


class RoleProtocolService:
    """Multi-agent role protocol service. Read-only; validates role
    boundaries, outputs, and transitions without auto-executing anything."""

    def __init__(self) -> None:
        pass

    # ── Read ─────────────────────────────────────────────────────────

    def list_roles(self) -> list[RoleProtocol]:
        """Return all 5 defined roles in canonical order."""
        return [_ROLES[r] for r in _ROLE_ORDER]

    def get_role(self, role_id: str) -> Optional[RoleProtocol]:
        """Get a single role definition by id."""
        return _ROLES.get(role_id)

    def role_ids(self) -> list[str]:
        """Return list of valid role ids."""
        return list(_ROLE_ORDER)

    # ── Validate ─────────────────────────────────────────────────────

    def validate_output(self, role_id: str, output_data: dict) -> ValidationResult:
        """Validate that output from a role satisfies its requirements."""
        role = self.get_role(role_id)
        if role is None:
            return ValidationResult(
                valid=False,
                message_cn=f"未知角色：{role_id}。可用角色：{', '.join(self.role_ids())}。",
                blocked=True,
            )

        details: list[str] = []
        requirements = role.output_requirements
        missing = [f"{f}：{r}" for f, r in requirements.items()
                   if f not in output_data or output_data[f] is None]
        if missing:
            details.append(f"缺少必要字段：{'; '.join(missing)}")

        has_evidence = bool(output_data.get("evidence_refs") or output_data.get("source_refs"))
        if not has_evidence:
            details.append("输出必须包含 evidence_refs 或 source_refs。")

        if role_id == "builder" and not output_data.get("tests") and not output_data.get("evidence_refs"):
            details.append("构建者输出必须包含测试结果或证据引用。")
        if role_id == "reviewer" and output_data.get("verdict", "") not in ("approved", "changes_requested", "blocked"):
            details.append("审查者必须输出明确的 verdict：approved/changes_requested/blocked。")
        if role_id == "skill_learner" and output_data.get("requires_father_approval") is not True:
            details.append("技能学习者提案必须标注 requires_father_approval=true。")

        if details:
            return ValidationResult(False, f"角色 {role.name_cn} 输出验证失败。", details)
        return ValidationResult(True, f"角色 {role.name_cn} 输出验证通过。")

    def explain_boundary(self, role_id: str) -> dict:
        """Return a Chinese explanation of this role's boundaries."""
        role = self.get_role(role_id)
        if role is None:
            return {"error": f"未知角色：{role_id}", "available_roles": self.role_ids()}
        return {
            "role_id": role.role_id, "name_cn": role.name_cn,
            "summary": f"{role.name_cn}（{role.role_id}）的角色边界：{role.description_cn}",
            "can_do": role.allowed_actions,
            "cannot_do": role.forbidden_actions,
            "output_must_have": dict(role.output_requirements),
            "can_handoff_to": [f"{_ROLES[r].name_cn}（{r}）" for r in role.can_transition_to],
            "note": "此边界描述为只读信息，不授权任何自动操作。",
        }

    def validate_transition(self, from_role_id: str, to_role_id: str) -> ValidationResult:
        """Validate a role-to-role transition. Hard blocks: unknown roles,
        invalid transitions."""
        from_role = self.get_role(from_role_id)
        to_role = self.get_role(to_role_id)
        ids = self.role_ids()

        if from_role is None:
            return ValidationResult(False, f"来源角色无效：{from_role_id}。", [f"可用：{', '.join(ids)}"], True)
        if to_role is None:
            return ValidationResult(False, f"目标角色无效：{to_role_id}。", [f"可用：{', '.join(ids)}"], True)

        if from_role_id == "builder" and to_role_id == "reviewer":
            return ValidationResult(True,
                "构建者→审查者移交需独立审查者上下文。",
                [_BUILDER_SELF_APPROVAL_MESSAGE])
        if from_role_id == "reviewer" and to_role_id == "builder":
            return ValidationResult(True,
                "审查者→构建者移交合法，但审查者不能自己实现发现。",
                [_REVIEWER_SELF_IMPLEMENT_MESSAGE])
        if to_role_id not in from_role.can_transition_to:
            return ValidationResult(False,
                f"{from_role.name_cn} 不能移交到 {to_role.name_cn}。",
                [f"允许目标：{', '.join(from_role.can_transition_to)}。"], True)

        return ValidationResult(True, f"转换 {from_role.name_cn}→{to_role.name_cn} 合法。")

    def get_handoff_format(self) -> dict:
        """Return the standard handoff format specification."""
        return {
            "format_cn": "角色间交接使用结构化 HandoffPackage",
            "fields": {
                "from_role": "来源角色 ID", "to_role": "目标角色 ID",
                "task_id": "关联任务 ID", "summary_cn": "中文交接摘要",
                "evidence_refs": "证据引用列表", "source_refs": "参考资料引用列表",
                "warnings": "已知风险和注意事项", "created_at": "ISO 8601 时间戳",
            },
            "note": "交接包为只读结构化数据，不自动触发任何执行。交接后需人工确认。",
            "required_fields": ["from_role", "to_role", "task_id", "summary_cn"],
        }

    def create_handoff(self, from_role_id: str, to_role_id: str, task_id: str,
                       summary_cn: str, evidence_refs: list[str] | None = None,
                       source_refs: list[str] | None = None,
                       warnings: list[str] | None = None) -> HandoffPackage:
        """Create a HandoffPackage after validating the transition."""
        transition = self.validate_transition(from_role_id, to_role_id)
        if transition.blocked:
            raise ValueError(transition.message_cn)
        return HandoffPackage(
            from_role=from_role_id, to_role=to_role_id, task_id=task_id,
            summary_cn=summary_cn, evidence_refs=evidence_refs or [],
            source_refs=source_refs or [], warnings=warnings or [],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def assert_not_self_approval(self, builder_context: str, reviewer_context: str) -> ValidationResult:
        """Check that builder and reviewer are not the same context."""
        if builder_context == reviewer_context:
            return ValidationResult(False, _BUILDER_SELF_APPROVAL_MESSAGE, [
                f"构建者上下文 '{builder_context}' 与审查者上下文相同。",
                "这是自我批准，不允许。请使用独立的审查者上下文。",
            ], True)
        return ValidationResult(True, "构建者与审查者上下文不同，非自我批准。")
