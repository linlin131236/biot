"""Patch Proposal. Standard unified-diff patch model with multi-file support,
validation, preview, and audit. Does NOT apply patches to real files."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from bolt_core.path_guard import PathGuard, PathCheck
from bolt_core.write_tool_proposal import (
    OP_CREATE, OP_DELETE, OP_MODIFY, OP_LABELS,
    RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL, RISK_LABELS,
    STATUS_PENDING, STATUS_LABELS,
)

# ── Budget constants ──
MAX_PATCH_LINES = 500
MAX_PATCH_FILES = 20
MAX_PATCH_SIZE_BYTES = 100 * 1024

# ── Blocked targets ──
_BLOCKED_DIRS = {".claude", ".bolt", ".git", "__pycache__", "node_modules", "venv", ".venv"}
_BLOCKED_NAMES = {"uv.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}


@dataclass(frozen=True)
class PatchFile:
    """A single file change within a patch."""
    file_path: str
    operation: str  # create / modify / delete
    hunks: list[dict] = field(default_factory=list)  # [{old_start, old_count, new_start, new_count, lines}]
    old_content: str = ""
    new_content: str = ""

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "operation": self.operation,
            "operation_label": OP_LABELS.get(self.operation, "未知"),
            "hunk_count": len(self.hunks),
            "hunks": self.hunks,
        }


@dataclass(frozen=True)
class PatchProposal:
    """Immutable multi-file patch proposal. Preview only, never auto-applied."""
    patch_id: str
    proposal_id: str | None  # Link to WriteProposal if created from one
    description: str
    files: list[PatchFile]
    unified_diff: str
    risk_level: str
    status: str = STATUS_PENDING
    total_lines: int = 0
    total_files: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audit_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "patch_id": self.patch_id,
            "proposal_id": self.proposal_id,
            "description": self.description,
            "files": [f.to_dict() for f in self.files],
            "unified_diff": self.unified_diff,
            "risk_level": self.risk_level,
            "risk_label": RISK_LABELS.get(self.risk_level, "未知"),
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, "未知"),
            "total_lines": self.total_lines,
            "total_files": self.total_files,
            "created_at": self.created_at,
            "audit_hash": self.audit_hash,
        }


@dataclass(frozen=True)
class PatchValidation:
    """Result of patch proposal validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    patch: PatchProposal | None = None

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "patch": self.patch.to_dict() if self.patch else None,
        }


class PatchProposalEngine:
    """Validates and creates patch proposals. Never applies patches to real files."""

    def __init__(self, project_dir: str = ".") -> None:
        self._project_dir = Path(project_dir).resolve()
        self._path_guard = PathGuard(project_dir)
        self._patches: dict[str, PatchProposal] = {}

    # ── Create ──

    def create(self, **fields) -> PatchValidation:
        """Validate and create a patch proposal."""
        errors: list[str] = []
        warnings: list[str] = []

        description = str(fields.get("description", ""))
        if not description.strip():
            errors.append("description（中文补丁说明）不能为空")

        files_data = fields.get("files", [])
        if not isinstance(files_data, list) or not files_data:
            errors.append("files 不能为空")
            return PatchValidation(valid=False, errors=errors)

        # ── Validate each file ──
        patch_files: list[PatchFile] = []
        for i, fdata in enumerate(files_data):
            if not isinstance(fdata, dict):
                errors.append(f"files[{i}] 必须是一个对象")
                continue

            file_path = str(fdata.get("file_path", "")).strip()
            if not file_path:
                errors.append(f"files[{i}].file_path 不能为空")
                continue

            operation = str(fdata.get("operation", OP_MODIFY))
            if operation not in OP_LABELS:
                errors.append(f"files[{i}].operation '{operation}' 无效")
                continue

            # Path security check
            check = self._check_path(file_path)
            if not check.allowed:
                errors.append(f"文件 '{file_path}' 被拒绝: {check.reason}")
                continue

            # Delete must be high risk
            if operation == OP_DELETE:
                warnings.append(f"文件 '{file_path}' 的删除操作将被标记为高风险")

            patch_files.append(PatchFile(
                file_path=file_path,
                operation=operation,
                hunks=list(fdata.get("hunks", [])),
                old_content=str(fdata.get("old_content", "")),
                new_content=str(fdata.get("new_content", "")),
            ))

        if not patch_files:
            errors.append("没有有效的文件变更")

        # ── Budget checks ──
        unified_diff = str(fields.get("unified_diff", ""))
        total_lines = unified_diff.count("\n") + 1 if unified_diff else 0
        if total_lines > MAX_PATCH_LINES:
            errors.append(f"补丁行数 {total_lines} 超过上限 {MAX_PATCH_LINES}")

        if len(patch_files) > MAX_PATCH_FILES:
            errors.append(f"修改文件数 {len(patch_files)} 超过上限 {MAX_PATCH_FILES}")

        # ── Risk assessment ──
        risk_level = str(fields.get("risk_level", RISK_LOW))
        has_delete = any(f.operation == OP_DELETE for f in patch_files)
        if has_delete and risk_level not in (RISK_HIGH, RISK_CRITICAL):
            risk_level = RISK_HIGH
            warnings.append("包含删除操作，风险等级自动提升为 high")

        if len(patch_files) > 10:
            if risk_level == RISK_LOW:
                risk_level = RISK_MEDIUM
                warnings.append("修改文件超过 10 个，风险等级提升为 medium")

        if errors:
            return PatchValidation(valid=False, errors=errors, warnings=warnings)

        # ── Create patch ──
        import hashlib
        audit_hash = hashlib.sha256(unified_diff.encode()).hexdigest()[:16] if unified_diff else ""

        patch = PatchProposal(
            patch_id=f"patch_{uuid4().hex[:12]}",
            proposal_id=str(fields.get("proposal_id", "")) or None,
            description=description,
            files=patch_files,
            unified_diff=unified_diff,
            risk_level=risk_level,
            total_lines=total_lines,
            total_files=len(patch_files),
            audit_hash=audit_hash,
        )
        self._patches[patch.patch_id] = patch
        return PatchValidation(valid=True, errors=[], warnings=warnings, patch=patch)

    # ── Query ──

    def get(self, patch_id: str) -> PatchProposal | None:
        return self._patches.get(patch_id)

    def list(self) -> list[PatchProposal]:
        return sorted(self._patches.values(), key=lambda p: p.created_at, reverse=True)

    def preview(self, patch_id: str) -> dict:
        """Return a safe preview of a patch. No apply."""
        patch = self._patches.get(patch_id)
        if patch is None:
            return {"error": f"补丁 '{patch_id}' 不存在"}
        return {
            "patch_id": patch.patch_id,
            "description": patch.description,
            "risk_level": patch.risk_level,
            "risk_label": RISK_LABELS.get(patch.risk_level, "未知"),
            "total_files": patch.total_files,
            "total_lines": patch.total_lines,
            "files": [{
                "path": f.file_path,
                "operation": OP_LABELS.get(f.operation, "未知"),
                "hunk_count": len(f.hunks),
            } for f in patch.files],
            "unified_diff": patch.unified_diff,
            "disclaimer": "此为补丁预览，未应用到任何真实文件。需要爸爸批准后才可 apply。",
        }

    # ── Internal ──

    def _check_path(self, target: str) -> PathCheck:
        check = self._path_guard.check(target)
        if not check.allowed:
            return check
        resolved = check.path
        parts = [p.lower() for p in resolved.parts]
        for blocked in _BLOCKED_DIRS:
            if blocked in parts:
                return PathCheck(False, resolved, f"禁止修改目录: {blocked}/")
        if resolved.name in _BLOCKED_NAMES:
            return PathCheck(False, resolved, f"禁止修改文件: {resolved.name}")
        return check
