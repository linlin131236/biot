"""Approval-gated Patch Apply. Only applies patches after human approval verification.

Implements the full closed loop:
  proposal → permission check → approval verification → re-check → apply → audit.
Never allows agent self-approve or approved=true bypass.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bolt_core.path_guard import PathGuard, PathCheck
from bolt_core.write_tool_proposal import WriteProposal, WriteProposalStore, STATUS_APPROVED, STATUS_APPLIED

# ── Apply result ──

@dataclass(frozen=True)
class ApplyResult:
    """Result of attempting to apply a proposal."""
    success: bool
    proposal_id: str
    reason: str
    audit_record: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "proposal_id": self.proposal_id,
            "reason": self.reason,
            "audit_record": self.audit_record,
        }


class ApprovalApplyEngine:
    """批准后应用补丁引擎。不自动执行 delete/push/release/tag。"""

    def __init__(self, store: WriteProposalStore, project_dir: str = ".") -> None:
        self._store = store
        self._project_dir = Path(project_dir).resolve()
        self._path_guard = PathGuard(project_dir)
        self._audit_log: list[dict] = []

    # ── Apply ──

    def apply(self, proposal_id: str, approval_record: dict) -> ApplyResult:
        """尝试应用一个已批准的提案。必须在所有检查通过后才执行。

        检查链：
        1. proposal 存在
        2. proposal 未过期（git HEAD 匹配）
        3. proposal 状态为 approved
        4. approval_record 存在
        5. actor 是人类（非 agent self-approve）
        6. approval scope 匹配 proposal
        7. 目标文件路径再次安全校验
        8. 不执行 delete/push/release/tag
        """
        # ── 1. Proposal exists ──
        proposal = self._store.get(proposal_id)
        if proposal is None:
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason=f"提案 '{proposal_id}' 不存在",
            )

        # ── 2. Check stale ──
        stale = self._store.check_stale(proposal_id)
        if stale.get("stale"):
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason=f"提案 '{proposal_id}' 已过期（git HEAD 已变更）。请重新创建提案。",
            )

        # ── 3. Status must be approved ──
        if proposal.status != STATUS_APPROVED:
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason=f"提案 '{proposal_id}' 状态为 '{proposal.status}'，不是 'approved'。必须先获得批准。",
            )

        # ── 4. Approval record must exist ──
        if not approval_record or not isinstance(approval_record, dict):
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason="缺少批准记录。写入操作必须有人工批准。",
            )

        # ── 5. Reject approved=true bypass ──
        if approval_record.get("approved") is True and not approval_record.get("actor"):
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason="检测到 approved=true 绕过尝试。不允许通过 API 参数直接批准。",
            )

        # ── 6. Actor must be human ──
        actor = str(approval_record.get("actor", "")).lower()
        if actor not in ("human", "father", "user", "爸爸"):
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason=f"Agent '{actor}' 不能自我批准。apply 必须由爸爸（human）授权。",
            )

        # ── 7. Scope must match ──
        approval_scope = str(approval_record.get("scope", ""))
        if approval_scope and approval_scope != proposal_id:
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason=f"批准范围 '{approval_scope}' 不匹配提案 '{proposal_id}'。",
            )

        # ── 8. Forged approval rejected ──
        if approval_record.get("forged") or approval_record.get("auto_generated"):
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason="批准记录包含伪造/自动生成标记，拒绝应用。",
            )

        # ── 9. Re-validate target paths ──
        for tf in proposal.target_files:
            check = self._path_guard.check(tf)
            if not check.allowed:
                return ApplyResult(
                    success=False, proposal_id=proposal_id,
                    reason=f"apply 前路径安全校验失败: {check.reason}（文件: {tf}）",
                )

        # ── 10. Block dangerous operations ──
        if proposal.operation_type == "delete":
            return ApplyResult(
                success=False, proposal_id=proposal_id,
                reason="删除操作不在本 milestone 自动执行范围内。请爸爸手动审查后执行。",
            )

        # ── 11. Apply the patch to real files ──
        files_changed: list[str] = []
        for tf in proposal.target_files:
            target_path = self._project_dir / tf
            try:
                if proposal.operation_type == "create":
                    # Extract new content from diff: all '+' lines after the hunk header
                    new_content = self._extract_new_content(proposal.diff_preview, tf)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(new_content, encoding="utf-8")
                elif proposal.operation_type == "modify":
                    # Apply unified diff to existing file
                    old_content = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
                    new_content = self._apply_unified_diff(old_content, proposal.diff_preview)
                    target_path.write_text(new_content, encoding="utf-8")
                else:
                    return ApplyResult(
                        success=False, proposal_id=proposal_id,
                        reason=f"不支持的操作类型: {proposal.operation_type}",
                    )
            except FileNotFoundError:
                return ApplyResult(
                    success=False, proposal_id=proposal_id,
                    reason=f"目标文件不存在: {tf}（modify 操作需要文件已存在）",
                )
            except OSError as e:
                return ApplyResult(
                    success=False, proposal_id=proposal_id,
                    reason=f"写入文件 '{tf}' 失败: {e}",
                )

            # ── Verify write ──
            if not target_path.exists():
                return ApplyResult(
                    success=False, proposal_id=proposal_id,
                    reason=f"写入验证失败：文件 '{tf}' 未被创建",
                )
            files_changed.append(tf)

        # ── All checks passed, files written ──
        self._store.mark_applied(proposal_id)

        # ── Record audit ──
        import hashlib as hl
        audit = {
            "proposal_id": proposal_id,
            "files_changed": files_changed,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "diff_hash": hl.sha256(proposal.diff_preview.encode()).hexdigest()[:16] if proposal.diff_preview else "",
            "rollback_hint": proposal.rollback_hint,
            "operation_type": proposal.operation_type,
            "result": "applied",
        }
        self._audit_log.append(audit)

        return ApplyResult(
            success=True, proposal_id=proposal_id,
            reason=f"提案 '{proposal_id}' 已应用。{len(files_changed)} 个文件已变更。",
            audit_record=audit,
        )

    def audit_log(self) -> list[dict]:
        """返回审计日志（只读）。"""
        return list(self._audit_log)

    # ── Patch application helpers ──

    @staticmethod
    def _apply_unified_diff(original: str, diff_text: str) -> str:
        """Apply a unified diff to original content. Returns new content."""
        original_lines = original.splitlines(keepends=True)
        result_lines: list[str] = []
        orig_idx = 0

        # Parse hunks from diff
        hunks = ApprovalApplyEngine._parse_hunks(diff_text)
        if not hunks:
            # No hunks to apply — return original
            return original

        for hunk in hunks:
            old_start, old_count, new_start, new_count, lines = hunk
            # Copy lines before this hunk
            while orig_idx < old_start - 1 and orig_idx < len(original_lines):
                result_lines.append(original_lines[orig_idx])
                orig_idx += 1

            # Skip removed lines in original
            skip_count = 0
            for line in lines:
                if line.startswith("-"):
                    skip_count += 1
                    orig_idx += 1
                elif line.startswith("+"):
                    result_lines.append(line[1:] + ("\n" if not line[1:].endswith("\n") else ""))
                else:
                    # Context line — keep from original
                    if orig_idx < len(original_lines):
                        result_lines.append(original_lines[orig_idx])
                    orig_idx += 1

        # Copy remaining original lines
        while orig_idx < len(original_lines):
            result_lines.append(original_lines[orig_idx])
            orig_idx += 1

        return "".join(result_lines)

    @staticmethod
    def _parse_hunks(diff_text: str) -> list[tuple[int, int, int, int, list[str]]]:
        """Parse unified diff hunks. Returns list of (old_start, old_count, new_start, new_count, lines)."""
        hunks: list[tuple[int, int, int, int, list[str]]] = []
        current_hunk: list[str] = []
        current_header: tuple[int, int, int, int] | None = None

        for line in diff_text.split("\n"):
            if line.startswith("@@") and " @@" in line:
                # Save previous hunk
                if current_header is not None and current_hunk:
                    hunks.append((*current_header, current_hunk))
                current_hunk = []
                # Parse @@ -old_start,old_count +new_start,new_count @@
                parts = line.split()
                if len(parts) >= 3:
                    old_part = parts[1].lstrip("-")
                    new_part = parts[2].lstrip("+")
                    try:
                        old_start = int(old_part.split(",")[0]) if old_part else 1
                        old_count = int(old_part.split(",")[1]) if "," in old_part else 1
                        new_start = int(new_part.split(",")[0]) if new_part else 1
                        new_count = int(new_part.split(",")[1]) if "," in new_part else 1
                        current_header = (old_start, old_count, new_start, new_count)
                    except (ValueError, IndexError):
                        current_header = (1, 0, 1, 0)
            elif current_header is not None and line and line[0] in (" ", "+", "-"):
                current_hunk.append(line)

        # Save last hunk
        if current_header is not None and current_hunk:
            hunks.append((*current_header, current_hunk))

        return hunks

    @staticmethod
    def _extract_new_content(diff_text: str, file_path: str) -> str:
        """Extract new file content from a 'create' diff — all '+' lines after removing the '+' prefix."""
        lines: list[str] = []
        in_file = False
        for line in diff_text.split("\n"):
            if line.startswith("+++ "):
                in_file = True
                continue
            if line.startswith("--- "):
                continue
            if line.startswith("@@") and " @@" in line:
                continue
            if in_file and line.startswith("+"):
                lines.append(line[1:])
        return "\n".join(lines) + "\n"
