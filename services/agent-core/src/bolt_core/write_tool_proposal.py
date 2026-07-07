"""Write Tool Proposal. Writes cannot modify files directly – they only generate
structured proposals that must be approved before application.

Does NOT write to real files. Does NOT land patches. All user-visible text is Chinese.
"""
from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from bolt_core.path_guard import PathGuard, PathCheck

# ── Statuses ──
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_APPLIED = "applied"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"
STATUS_STALE = "stale"

STATUS_LABELS: dict[str, str] = {
    STATUS_PENDING: "待批准",
    STATUS_APPROVED: "已批准",
    STATUS_APPLIED: "已应用",
    STATUS_CANCELLED: "已取消",
    STATUS_EXPIRED: "已过期",
    STATUS_STALE: "已过期（HEAD 变更）",
}

# ── Operation types ──
OP_CREATE = "create"
OP_MODIFY = "modify"
OP_DELETE = "delete"

OP_LABELS: dict[str, str] = {
    OP_CREATE: "新建",
    OP_MODIFY: "修改",
    OP_DELETE: "删除",
}

# ── Risk levels ──
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

RISK_LABELS: dict[str, str] = {
    RISK_LOW: "低",
    RISK_MEDIUM: "中",
    RISK_HIGH: "高",
    RISK_CRITICAL: "严重",
}

# ── Blocked dirs / names for target files ──
_BLOCKED_TARGET_DIRS = {".claude", ".bolt", ".git", "__pycache__", "node_modules", "venv", ".venv"}
_BLOCKED_TARGET_NAMES = {"uv.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}


@dataclass(frozen=True)
class WriteProposal:
    """Immutable write proposal. Must be approved before application."""
    proposal_id: str
    tool_id: str
    target_files: list[str]
    operation_type: str
    before_summary: str
    after_summary: str
    diff_preview: str
    risk_level: str
    required_permissions: list[str]
    rollback_hint: str
    chinese_explanation: str
    git_head: str
    status: str = STATUS_PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "tool_id": self.tool_id,
            "target_files": self.target_files,
            "operation_type": self.operation_type,
            "operation_label": OP_LABELS.get(self.operation_type, "未知"),
            "before_summary": self.before_summary,
            "after_summary": self.after_summary,
            "diff_preview": self.diff_preview,
            "risk_level": self.risk_level,
            "risk_label": RISK_LABELS.get(self.risk_level, "未知"),
            "required_permissions": self.required_permissions,
            "rollback_hint": self.rollback_hint,
            "chinese_explanation": self.chinese_explanation,
            "git_head": self.git_head,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, "未知"),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ProposalValidation:
    """Result of validating a proposal before creation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    proposal: WriteProposal | None = None

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "proposal": self.proposal.to_dict() if self.proposal else None,
        }


class WriteProposalStore:
    """管理写入提案。不写文件，不落地 patch。"""

    def __init__(self, project_dir: str = ".") -> None:
        self._project_dir = Path(project_dir).resolve()
        self._path_guard = PathGuard(project_dir)
        self._proposals: dict[str, WriteProposal] = {}

    # ── CRUD ──

    def create(self, **fields) -> ProposalValidation:
        """创建写入提案。验证路径安全后生成不可变 proposal。"""
        errors: list[str] = []

        # ── Validate required fields ──
        tool_id = str(fields.get("tool_id", "")).strip()
        if not tool_id:
            errors.append("tool_id 不能为空")

        target_files = fields.get("target_files", [])
        if not isinstance(target_files, list) or not target_files:
            errors.append("target_files 不能为空，必须是文件路径列表")
            target_files = []

        operation_type = str(fields.get("operation_type", OP_MODIFY))
        if operation_type not in OP_LABELS:
            errors.append(f"operation_type 无效: {operation_type}，合法值: {list(OP_LABELS)}")

        # ── Validate each target file ──
        validated_files: list[str] = []
        for tf in target_files:
            tf_str = str(tf).strip()
            if not tf_str:
                continue
            check = self._check_target(tf_str, operation_type)
            if not check.allowed:
                errors.append(f"目标文件 '{tf_str}' 被拒绝: {check.reason}")
            else:
                validated_files.append(tf_str)

        if not validated_files:
            errors.append("没有有效的目标文件")

        # ── Delete operation requires high risk ──
        risk_level = str(fields.get("risk_level", RISK_LOW))
        if operation_type == OP_DELETE and risk_level not in (RISK_HIGH, RISK_CRITICAL):
            errors.append("删除操作必须标记为 high 或 critical 风险")

        if errors:
            return ProposalValidation(valid=False, errors=errors)

        # ── Get current git HEAD ──
        git_head = self._get_git_head()

        proposal = WriteProposal(
            proposal_id=f"proposal_{uuid4().hex[:12]}",
            tool_id=tool_id,
            target_files=validated_files,
            operation_type=operation_type,
            before_summary=str(fields.get("before_summary", "")),
            after_summary=str(fields.get("after_summary", "")),
            diff_preview=str(fields.get("diff_preview", "")),
            risk_level=risk_level,
            required_permissions=list(fields.get("required_permissions", [])),
            rollback_hint=str(fields.get("rollback_hint", "")),
            chinese_explanation=str(fields.get("chinese_explanation", "")),
            git_head=git_head,
        )
        self._proposals[proposal.proposal_id] = proposal
        return ProposalValidation(valid=True, proposal=proposal)

    def get(self, proposal_id: str) -> WriteProposal | None:
        return self._proposals.get(proposal_id)

    def list(self, status: str | None = None) -> list[WriteProposal]:
        result = list(self._proposals.values())
        if status:
            result = [p for p in result if p.status == status]
        result.sort(key=lambda p: p.created_at, reverse=True)
        return result

    def cancel(self, proposal_id: str) -> bool:
        p = self._proposals.get(proposal_id)
        if p is None or p.status not in (STATUS_PENDING, STATUS_APPROVED):
            return False
        # Create a new instance with updated status
        self._proposals[proposal_id] = WriteProposal(
            proposal_id=p.proposal_id, tool_id=p.tool_id,
            target_files=p.target_files, operation_type=p.operation_type,
            before_summary=p.before_summary, after_summary=p.after_summary,
            diff_preview=p.diff_preview, risk_level=p.risk_level,
            required_permissions=p.required_permissions,
            rollback_hint=p.rollback_hint,
            chinese_explanation=p.chinese_explanation,
            git_head=p.git_head, status=STATUS_CANCELLED,
            created_at=p.created_at,
        )
        return True

    def check_stale(self, proposal_id: str) -> dict:
        """检查 proposal 是否因 git HEAD 变化而过期。"""
        p = self._proposals.get(proposal_id)
        if p is None:
            return {"stale": True, "reason": f"提案 '{proposal_id}' 不存在"}
        current_head = self._get_git_head()
        is_stale = current_head != p.git_head
        if is_stale and p.status == STATUS_PENDING:
            # Auto-mark as stale
            self._proposals[proposal_id] = WriteProposal(
                proposal_id=p.proposal_id, tool_id=p.tool_id,
                target_files=p.target_files, operation_type=p.operation_type,
                before_summary=p.before_summary, after_summary=p.after_summary,
                diff_preview=p.diff_preview, risk_level=p.risk_level,
                required_permissions=p.required_permissions,
                rollback_hint=p.rollback_hint,
                chinese_explanation=p.chinese_explanation,
                git_head=p.git_head, status=STATUS_STALE,
                created_at=p.created_at,
            )
        return {
            "proposal_id": proposal_id,
            "stale": is_stale,
            "proposal_head": p.git_head[:8] if p.git_head else "未知",
            "current_head": current_head[:8] if current_head else "未知",
            "status": self._proposals[proposal_id].status,
        }

    def mark_applied(self, proposal_id: str) -> bool:
        p = self._proposals.get(proposal_id)
        if p is None or p.status != STATUS_APPROVED:
            return False
        self._proposals[proposal_id] = WriteProposal(
            proposal_id=p.proposal_id, tool_id=p.tool_id,
            target_files=p.target_files, operation_type=p.operation_type,
            before_summary=p.before_summary, after_summary=p.after_summary,
            diff_preview=p.diff_preview, risk_level=p.risk_level,
            required_permissions=p.required_permissions,
            rollback_hint=p.rollback_hint,
            chinese_explanation=p.chinese_explanation,
            git_head=p.git_head, status=STATUS_APPLIED,
            created_at=p.created_at,
        )
        return True

    def __len__(self) -> int:
        return len(self._proposals)

    # ── Internal ──

    def _check_target(self, target: str, operation: str) -> PathCheck:
        """Validate a target file path for write operations."""
        check = self._path_guard.check(target)
        if not check.allowed:
            return check

        resolved = check.path
        parts = [p.lower() for p in resolved.parts]

        for blocked in _BLOCKED_TARGET_DIRS:
            if blocked in parts:
                return PathCheck(False, resolved, f"禁止写入目录: {blocked}/")

        if resolved.name in _BLOCKED_TARGET_NAMES:
            return PathCheck(False, resolved, f"禁止写入文件: {resolved.name}")

        return check

    def _get_git_head(self) -> str:
        """Get the current git HEAD hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self._project_dir), capture_output=True,
                text=True, timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"
