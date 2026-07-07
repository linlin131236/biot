"""Read-only release readiness assessment. Never fixes or executes."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from bolt_core.execution_audit_store import ExecutionAuditStore, ExecutionAuditStoreError
from bolt_core.execution_audit_integrity import ExecutionAuditIntegrityService
from bolt_core.evidence_redactor import _PATTERNS


class ReleaseReadinessService:
    def __init__(self, project_dir: str, audit_store: ExecutionAuditStore) -> None:
        self._project_dir = Path(project_dir)
        self._audit_store = audit_store
        self._integrity = ExecutionAuditIntegrityService(audit_store)

    def assess(self) -> dict:
        checks: list[dict] = []
        blockers: list[str] = []
        warnings: list[str] = []

        # 1. Integrity check
        integrity_results = self._integrity.list_integrity()
        integrity_blocking = [d for d in integrity_results if d["severity"] == "blocking"]
        checks.append(_check(
            "integrity",
            "审计文件完整性",
            len(integrity_blocking) == 0,
            "blocking" if integrity_blocking else "info",
            "审计文件结构正常" if not integrity_blocking else f"审计文件存在 {len(integrity_blocking)} 个阻断问题",
        ))
        if integrity_blocking:
            blockers.append("审计文件完整性检查未通过")

        # 2. Secret plaintext scan
        secret_found = self._scan_secrets()
        checks.append(_check(
            "secret_scan",
            "审计文件敏感信息扫描",
            not secret_found,
            "blocking" if secret_found else "info",
            "未发现明文敏感信息" if not secret_found else "审计文件中发现明文敏感信息",
        ))
        if secret_found:
            blockers.append("审计文件包含明文敏感信息")

        # 3. Git clean check
        git_clean = self._git_clean()
        checks.append(_check(
            "git_clean",
            "代码工作区干净",
            git_clean,
            "blocking" if not git_clean else "info",
            "工作区无未提交改动" if git_clean else "工作区存在未提交的源码改动",
        ))
        if not git_clean:
            blockers.append("代码工作区不干净，存在未提交改动")

        # 4. Branch sync check
        branch_synced = self._branch_synced()
        checks.append(_check(
            "branch_sync",
            "分支与远程同步",
            branch_synced,
            "warning" if not branch_synced else "info",
            "本地分支与 origin 已同步" if branch_synced else "本地分支与 origin 不同步",
        ))
        if not branch_synced:
            warnings.append("本地分支与远程不同步")

        # 5. Docs consistency
        docs_ok = self._docs_consistent()
        checks.append(_check(
            "docs_consistency",
            "项目文档一致性",
            docs_ok,
            "warning" if not docs_ok else "info",
            "project-state.md 与 phase gate 一致" if docs_ok else "project-state.md 与最新 phase gate 不一致",
        ))
        if not docs_ok:
            warnings.append("项目文档不一致")

        # 6. Review gate exists
        gate_exists = self._review_gate_exists()
        checks.append(_check(
            "review_gate",
            "阶段审查门存在",
            gate_exists,
            "warning" if not gate_exists else "info",
            "最新 phase review gate 存在" if gate_exists else "最新 phase review gate 缺失",
        ))
        if not gate_exists:
            warnings.append("缺少阶段审查门文档")

        ready = len(blockers) == 0
        return {
            "ready": ready,
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
        }

    def _scan_secrets(self) -> bool:
        """Return True if any PLAINTEXT secret pattern found in audit JSON.
        Excludes already-redacted placeholders like '[已脱敏]' from M56 redaction.
        Handles both literal Chinese and JSON-escaped \\uXXXX forms.
        """
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
        """Return True if no staged/unstaged source changes."""
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
                # Ignore generated/cache files
                if any(pat in line for pat in [".bolt/", "node_modules/", "__pycache__/", ".pytest_cache/", "uv.lock", "pnpm-lock.yaml"]):
                    continue
                return False
            return True
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _branch_synced(self) -> bool:
        """Return True if HEAD equals origin/main (read-only check)."""
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
        """Check project-state.md mentions the latest phase and the
        corresponding phase review gate exists."""
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
        """Check if a phase-{n}-review-gate.md exists for the current milestone.
        Scans all phase-*-review-gate.md files and picks the highest number,
        then compares against the current milestone from project-state.md."""
        current = self._parse_current_milestone()
        docs_dir = self._project_dir / "docs"
        if not docs_dir.exists():
            return False
        import re
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
        """Extract milestone number from docs/project-state.md.
        Looks for pattern: '已完成到：M{number}'."""
        state_path = self._project_dir / "docs" / "project-state.md"
        if not state_path.exists():
            return None
        try:
            content = state_path.read_text(encoding="utf-8")
            import re
            m = re.search(r"已完成到：M(\d+)", content)
            if m:
                return int(m.group(1))
        except OSError:
            pass
        return None


def _check(code: str, label: str, passed: bool, severity: str, detail: str) -> dict:
    return {
        "code": code,
        "label": label,
        "passed": passed,
        "severity": severity,
        "severity_label": "阻断" if severity == "blocking" else ("警告" if severity == "warning" else "提示"),
        "detail": detail,
    }
