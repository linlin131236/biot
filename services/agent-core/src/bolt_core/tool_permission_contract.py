"""Tool Permission Contract. Binds tool calls to PermissionGate.

Defines permission levels, evaluates requirements, and verifies approvals.
Does NOT execute tools. Does NOT auto-approve.
"""
from __future__ import annotations

from dataclasses import dataclass, field

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
    ToolDef,
    ToolRegistry,
)

# ── Permission levels ──
LEVEL_NONE = "none"
LEVEL_READ = "read"
LEVEL_WRITE = "write"
LEVEL_EXECUTE = "execute"
LEVEL_DANGEROUS = "dangerous"

PERMISSION_LEVELS = {LEVEL_NONE, LEVEL_READ, LEVEL_WRITE, LEVEL_EXECUTE, LEVEL_DANGEROUS}

LEVEL_LABELS: dict[str, str] = {
    LEVEL_NONE: "无需权限",
    LEVEL_READ: "只读权限",
    LEVEL_WRITE: "写入权限",
    LEVEL_EXECUTE: "执行权限",
    LEVEL_DANGEROUS: "危险权限",
}

# ── Permission levels requiring human approval ──
_HUMAN_APPROVAL_LEVELS = {LEVEL_WRITE, LEVEL_EXECUTE, LEVEL_DANGEROUS}

# ── Operations always considered dangerous ──
_ALWAYS_DANGEROUS_OPS = {
    "push", "release", "tag", "delete", "force_push", "hard_reset",
    "credential_read", "credential_write", "secret_read", "secret_write",
    "cert_read", "cert_write", "permission_approve", "permission_bypass",
}

# ── Category → minimum permission mapping ──
_CATEGORY_MIN_PERM: dict[str, str] = {
    CATEGORY_READ_ONLY: LEVEL_READ,
    CATEGORY_SIDE_EFFECT: LEVEL_WRITE,
    CATEGORY_WRITE: LEVEL_WRITE,
    CATEGORY_DANGEROUS: LEVEL_DANGEROUS,
}

# ── Decisions ──
DECISION_ALLOWED = "allowed"
DECISION_DENIED = "denied"
DECISION_NEEDS_APPROVAL = "needs_approval"

DECISION_LABELS: dict[str, str] = {
    DECISION_ALLOWED: "允许执行",
    DECISION_DENIED: "拒绝执行",
    DECISION_NEEDS_APPROVAL: "需要批准",
}


@dataclass(frozen=True)
class PermissionDecision:
    """Immutable result of permission evaluation."""
    tool_id: str
    decision: str
    reason: str
    required_level: str = LEVEL_NONE
    human_approval_required: bool = False
    required_approval_by: str = ""
    denied_ops: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "decision": self.decision,
            "decision_label": DECISION_LABELS.get(self.decision, "未知"),
            "reason": self.reason,
            "required_level": self.required_level,
            "required_level_label": LEVEL_LABELS.get(self.required_level, "未知"),
            "human_approval_required": self.human_approval_required,
            "required_approval_by": self.required_approval_by,
            "denied_ops": self.denied_ops,
        }


@dataclass(frozen=True)
class ApprovalVerification:
    """Result of verifying an approval record."""
    valid: bool
    reason: str
    checks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "checks": self.checks,
        }


class PermissionContractEngine:
    """Evaluates permission requirements. Does NOT execute or auto-approve."""

    @staticmethod
    def evaluate(
        tool_id: str,
        operation: str = "",
        registry: ToolRegistry | None = None,
    ) -> PermissionDecision:
        """Evaluate whether a tool operation requires permission/approval."""
        # ── Check if operation is always dangerous ──
        op_lower = operation.lower().strip() if operation else ""
        if op_lower in _ALWAYS_DANGEROUS_OPS:
            return PermissionDecision(
                tool_id=tool_id,
                decision=DECISION_NEEDS_APPROVAL,
                reason=f"操作 '{operation}' 属于永久危险操作，必须获得爸爸明确批准。",
                required_level=LEVEL_DANGEROUS,
                human_approval_required=True,
                required_approval_by="human",
            )

        # ── Unknown tool ──
        tool_def = registry.get(tool_id) if registry else None
        if tool_def is None:
            return PermissionDecision(
                tool_id=tool_id,
                decision=DECISION_DENIED,
                reason=f"工具 '{tool_id}' 未注册。未知工具默认禁止执行。",
                required_level=LEVEL_DANGEROUS,
            )

        # ── Determine required level from category ──
        required_level = _CATEGORY_MIN_PERM.get(tool_def.category, LEVEL_DANGEROUS)
        human_approval = required_level in _HUMAN_APPROVAL_LEVELS

        # ── Read-only: allowed without approval ──
        if tool_def.category == CATEGORY_READ_ONLY and required_level == LEVEL_READ:
            return PermissionDecision(
                tool_id=tool_id,
                decision=DECISION_ALLOWED,
                reason="只读工具，低风险，无需人工批准即可执行。",
                required_level=required_level,
                human_approval_required=False,
            )

        # ── Dangerous: always needs approval ──
        if tool_def.category == CATEGORY_DANGEROUS or required_level == LEVEL_DANGEROUS:
            return PermissionDecision(
                tool_id=tool_id,
                decision=DECISION_NEEDS_APPROVAL,
                reason=f"危险工具 '{tool_def.display_name}'，必须获得爸爸在 PermissionGate 中明确批准后才可执行。",
                required_level=LEVEL_DANGEROUS,
                human_approval_required=True,
                required_approval_by="human",
            )

        # ── Write/Execute/Side-effect: needs approval ──
        if human_approval:
            level_label = LEVEL_LABELS.get(required_level, required_level)
            return PermissionDecision(
                tool_id=tool_id,
                decision=DECISION_NEEDS_APPROVAL,
                reason=f"工具 '{tool_def.display_name}' 需要{level_label}，必须获得人工批准。",
                required_level=required_level,
                human_approval_required=True,
                required_approval_by="human",
            )

        # ── Default: denied ──
        return PermissionDecision(
            tool_id=tool_id,
            decision=DECISION_DENIED,
            reason=f"无法确定工具 '{tool_id}' 的权限需求，默认拒绝。",
        )

    @staticmethod
    def verify_approval(
        decision: PermissionDecision,
        approval_record: dict,
    ) -> ApprovalVerification:
        """Verify an approval record against a permission decision.

        Rejects: approved=true bypass, agent self-approval, scope mismatch,
        missing approval, expired approval.
        """
        checks: list[dict] = []

        # ── 1. Approval must exist ──
        if not approval_record or not isinstance(approval_record, dict):
            return ApprovalVerification(
                valid=False,
                reason="缺少批准记录。write/execute/dangerous 工具必须有人工批准。",
                checks=[{"check": "approval_exists", "passed": False, "detail": "批准记录为空"}],
            )

        # ── 2. Reject approved=true bypass ──
        if approval_record.get("approved") is True and not approval_record.get("actor"):
            checks.append({
                "check": "no_approved_true_bypass",
                "passed": False,
                "detail": "不允许通过 approved=true 直接绕过批准。必须提供有效 actor。",
            })
            return ApprovalVerification(
                valid=False,
                reason="检测到 approved=true 绕过尝试。不允许通过 API 参数直接批准。",
                checks=checks,
            )

        # ── 3. Actor must be human ──
        actor = str(approval_record.get("actor", "")).lower()
        if actor not in ("human", "father", "user", "爸爸"):
            checks.append({
                "check": "actor_is_human",
                "passed": False,
                "detail": f"批准人 '{actor}' 不是人类。Agent 不允许 self-approve。",
            })
            return ApprovalVerification(
                valid=False,
                reason=f"Agent '{actor}' 不能自我批准。批准必须由爸爸（human）执行。",
                checks=checks,
            )
        checks.append({
            "check": "actor_is_human",
            "passed": True,
            "detail": f"批准人: {actor}",
        })

        # ── 4. Scope must match ──
        approval_scope = str(approval_record.get("scope", ""))
        if approval_scope and approval_scope != decision.tool_id:
            checks.append({
                "check": "scope_matches",
                "passed": False,
                "detail": f"批准范围 '{approval_scope}' 不匹配工具 '{decision.tool_id}'",
            })
            return ApprovalVerification(
                valid=False,
                reason=f"批准范围不匹配：批准的是 '{approval_scope}'，但需要批准的是 '{decision.tool_id}'。",
                checks=checks,
            )
        checks.append({
            "check": "scope_matches",
            "passed": True,
            "detail": f"批准范围: {decision.tool_id}",
        })

        # ── 5. Approval must not be forged ──
        if approval_record.get("forged") or approval_record.get("auto_generated"):
            checks.append({
                "check": "not_forged",
                "passed": False,
                "detail": "批准记录包含伪造/自动生成标记",
            })
            return ApprovalVerification(
                valid=False,
                reason="批准记录被标记为伪造或自动生成，拒绝。",
                checks=checks,
            )
        checks.append({
            "check": "not_forged",
            "passed": True,
            "detail": "批准记录来源合法",
        })

        return ApprovalVerification(
            valid=True,
            reason="批准验证通过。",
            checks=checks,
        )

    @staticmethod
    def list_dangerous_ops() -> dict:
        """Return the list of operations always classified as dangerous."""
        return {
            "always_dangerous_ops": sorted(_ALWAYS_DANGEROUS_OPS),
            "total": len(_ALWAYS_DANGEROUS_OPS),
            "disclaimer": "这些操作在任何上下文中都需要爸爸明确批准，不可自动执行。",
        }
