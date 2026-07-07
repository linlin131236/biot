"""Local release checklist. Read-only, never auto-releases."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from bolt_core.evidence_redactor import _PATTERNS
from bolt_core.execution_audit_integrity import ExecutionAuditIntegrityService
from bolt_core.execution_audit_store import ExecutionAuditStore


class LocalReleaseChecklistService:
    """Produce a human-readable checklist for local release readiness.
    Does NOT execute any release, tag, push, or delete action.
    """

    def __init__(self, project_dir: str, audit_store: ExecutionAuditStore) -> None:
        self._project_dir = Path(project_dir)
        self._audit_store = audit_store
        self._integrity = ExecutionAuditIntegrityService(audit_store)

    def checklist(self) -> dict:
        items: list[dict] = []
        blockers: list[str] = []
        warnings: list[str] = []

        # ── 审计完整性 ──
        integrity_results = self._integrity.list_integrity()
        integrity_blocking = [d for d in integrity_results if d["severity"] == "blocking"]
        if integrity_blocking:
            items.append(_item(
                "audit_structure", "审计完整性", "审计文件结构完整",
                "fail",
                f"审计文件存在 {len(integrity_blocking)} 个阻断问题",
                "建议：检查 execution-audit.json 文件是否被手动编辑损坏，可从备份恢复",
            ))
            blockers.append("审计文件结构损坏")
        elif integrity_results:
            items.append(_item(
                "audit_structure", "审计完整性", "审计文件结构完整",
                "warn",
                f"审计文件存在 {len(integrity_results)} 个非阻断问题",
                "建议：检查诊断信息后决定是否忽略",
            ))
            warnings.append("审计文件存在非阻断问题")
        else:
            items.append(_item(
                "audit_structure", "审计完整性", "审计文件结构完整",
                "pass",
                "审计文件结构正常，无诊断问题",
                None,
            ))

        # ── 证据安全 ──
        secret_found = self._scan_secrets()
        if secret_found:
            items.append(_item(
                "secret_scan", "证据安全", "审计文件无明文敏感信息",
                "fail",
                "审计文件中发现明文密钥/Token/证书",
                "建议：对执行证据运行脱敏（M56 evidence_redactor），确保所有凭证已替换为 [已脱敏]",
            ))
            blockers.append("审计文件包含明文敏感信息")
        else:
            items.append(_item(
                "secret_scan", "证据安全", "审计文件无明文敏感信息",
                "pass",
                "未发现明文密钥/Token/证书，脱敏检查通过",
                None,
            ))

        # ── 代码工作区 ──
        git_clean = self._git_clean()
        if not git_clean:
            items.append(_item(
                "git_clean", "代码状态", "工作区无未提交源码改动",
                "fail",
                "工作区存在未提交的源码改动",
                "建议：提交或暂存改动后重新检查。注意：不提交生成物和缓存文件",
            ))
            blockers.append("代码工作区不干净")
        else:
            items.append(_item(
                "git_clean", "代码状态", "工作区无未提交源码改动",
                "pass",
                "工作区干净，无待提交源码改动",
                None,
            ))

        # ── 分支同步 ──
        branch_synced = self._branch_synced()
        if not branch_synced:
            items.append(_item(
                "branch_sync", "分支同步", "本地分支与 origin/main 一致",
                "warn",
                "本地分支与 origin/main 不一致",
                "建议：git push 或 git pull 同步后再发布。注意：仅在爸爸明确确认后执行",
            ))
            warnings.append("本地分支与远程不同步")
        else:
            items.append(_item(
                "branch_sync", "分支同步", "本地分支与 origin/main 一致",
                "pass",
                "本地 HEAD 与 origin/main 一致",
                None,
            ))

        # ── 文档一致性 ──
        docs_ok = self._docs_consistent()
        if not docs_ok:
            items.append(_item(
                "docs_state", "文档状态", "project-state.md 记载最新 milestone",
                "warn",
                "project-state.md 与最新 phase gate 不一致或无法解析",
                "建议：更新 docs/project-state.md 的「已完成到：M{n}」字段",
            ))
            warnings.append("项目文档未同步")
        else:
            items.append(_item(
                "docs_state", "文档状态", "project-state.md 记载最新 milestone",
                "pass",
                "project-state.md 与最新 phase gate 一致",
                None,
            ))

        # ── 审查门 ──
        gate_exists = self._review_gate_exists()
        if not gate_exists:
            items.append(_item(
                "review_gate", "审查门", "最新 phase review gate 存在",
                "warn",
                "最新 phase review gate 文档缺失",
                "建议：为当前 milestone 创建 docs/phase-{n}-review-gate.md",
            ))
            warnings.append("缺少阶段审查门文档")
        else:
            items.append(_item(
                "review_gate", "审查门", "最新 phase review gate 存在",
                "pass",
                "最新 phase review gate 文档已就位",
                None,
            ))

        # ── 发布确认（尊重规则） ──
        items.append(_item(
            "release_confirm", "发布确认", "未自动执行 release/tag/delete",
            "pass",
            "本检查清单为只读，不执行任何发布操作。release 需由爸爸在终端人工执行",
            None,
        ))

        ready = len(blockers) == 0
        if ready:
            next_step = "所有阻断项已通过。可以准备发布，但发布操作需由爸爸在终端人工执行。"
        else:
            next_step = f"存在 {len(blockers)} 个阻断项，请先解决后再发布。解决建议见各条目 recommendation。"

        return {
            "ready": ready,
            "items": items,
            "blockers": blockers,
            "warnings": warnings,
            "next_step": next_step,
            "disclaimer": "此检查清单为只读诊断工具，不自动执行任何发布、标签、推送或删除操作。",
        }

    # ── 内部检查方法（只读） ──

    def _scan_secrets(self) -> bool:
        """Return True if any PLAINTEXT secret found, excluding redacted placeholders."""
        if not self._audit_store._path.exists():
            return False
        try:
            raw = self._audit_store._path.read_text(encoding="utf-8")
        except OSError:
            return False
        redacted_markers = ("[已脱敏]", "[\\u5df2\\u8131\\u654f]")
        for pattern, _ in _PATTERNS:
            for match in pattern.finditer(raw):
                matched = match.group()
                if not any(marker in matched for marker in redacted_markers):
                    return True
        return False

    def _git_clean(self) -> bool:
        """Return True if no staged/unstaged source changes (ignoring generated/cache)."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self._project_dir),
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return False
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if any(pat in line for pat in [".bolt/", "node_modules/", "__pycache__/", ".pytest_cache/", "uv.lock", "pnpm-lock.yaml"]):
                    continue
                return False
            return True
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _branch_synced(self) -> bool:
        """Return True if HEAD equals origin/main (read-only git query)."""
        try:
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self._project_dir),
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            origin = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=str(self._project_dir),
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            return bool(head) and head == origin
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _docs_consistent(self) -> bool:
        """Check project-state.md mentions the latest milestone."""
        current = self._parse_current_milestone()
        if current is None:
            return False
        state_path = self._project_dir / "docs" / "project-state.md"
        try:
            content = state_path.read_text(encoding="utf-8")
            expect = f"已完成到：M{current}"
            return expect in content
        except OSError:
            return False

    def _review_gate_exists(self) -> bool:
        """Check if a phase-{n}-review-gate.md exists for the current milestone."""
        current = self._parse_current_milestone()
        docs_dir = self._project_dir / "docs"
        if not docs_dir.exists():
            return False
        highest = 0
        pat = re.compile(r"^phase-(\d+)-review-gate\.md$")
        try:
            for entry in docs_dir.iterdir():
                m = pat.match(entry.name)
                if m:
                    n = int(m.group(1))
                    if n > highest:
                        highest = n
        except OSError:
            pass
        if current is None:
            return highest > 0
        return highest >= current

    def _parse_current_milestone(self) -> int | None:
        """Extract milestone number from docs/project-state.md."""
        state_path = self._project_dir / "docs" / "project-state.md"
        if not state_path.exists():
            return None
        try:
            content = state_path.read_text(encoding="utf-8")
            m = re.search(r"已完成到：M(\d+)", content)
            if m:
                return int(m.group(1))
        except OSError:
            pass
        return None


def _item(code: str, category: str, label: str, status: str, detail: str, recommendation: str | None) -> dict:
    status_label = {"pass": "✅ 通过", "fail": "❌ 阻断", "warn": "⚠️ 警告"}.get(status, status)
    return {
        "code": code,
        "category": category,
        "label": label,
        "status": status,
        "status_label": status_label,
        "detail": detail,
        "recommendation": recommendation,
    }
