"""M124 privacy and security audit. Read-only assessment only."""
from __future__ import annotations

from bolt_core.beta_reliability_common import BetaCheck, BetaReadinessBase, BetaReviewResult, check


class PrivacySecurityAuditService(BetaReadinessBase):
    def review(self) -> BetaReviewResult:
        checks: list[BetaCheck] = []
        modules = [
            ("证据脱敏存在", "evidence_redactor"),
            ("记忆权限边界存在", "memory_permission_boundary"),
            ("工具权限契约存在", "tool_permission_contract"),
            ("人工批准写入边界存在", "approval_apply"),
            ("只读工具运行器存在", "readonly_tool_runner"),
        ]
        for label, module in modules:
            path = self.src(module)
            checks.append(check(label, path.exists(), f"{path.name} {'存在' if path.exists() else '缺失'}"))

        desktop = self.project_dir / "apps/desktop/src"
        renderer_hits = self._renderer_exposure_hits(desktop)
        checks.append(check("renderer 无危险暴露", not renderer_hits, "; ".join(renderer_hits[:5]) if renderer_hits else "未发现 renderer 危险暴露"))

        type_hits = self.scan_files([desktop], ["as any", "unknown as"])
        checks.append(check("无 as any / unknown as", not type_hits, "; ".join(type_hits[:5]) if type_hits else "未发现 TypeScript 类型逃逸"))

        audit_doc = self.read(self.docs("release/privacy-security-audit.md")).lower()
        required = ["prompt injection", "permission", "secret", "supply chain", "privacy", "readonly"]
        audit_doc_ok = all(term in audit_doc for term in required)
        checks.append(check("隐私安全审计清单完整", audit_doc_ok, "需覆盖 prompt injection、权限、secret、供应链、隐私和只读审计"))

        jlens = self.docs("references/anthropic-jlens-global-workspace-2026.md")
        checks.append(check("J-lens 研究参考只作只读风险信号", jlens.exists(), f"{jlens.name} {'存在' if jlens.exists() else '缺失'}"))

        docs_ok = self.milestone_docs_complete(124)
        checks.append(check("M124 文档链完整", docs_ok, "exec plan / decision / review gate 已就位" if docs_ok else "M124 文档链缺失"))

        state = self.read(self.docs("project-state.md"))
        boundary_ok = "M124" in state and "未进入 M125" in state
        checks.append(check("M125 边界未越过", boundary_ok, "project-state 记录 M124 且未进入 M125"))

        return BetaReviewResult(
            checks=checks[:9],
            next_step="等待爸爸复审 M124；隐私安全审计只提供风险信号，不会替代 PermissionGate。",
        )

    def _renderer_exposure_hits(self, desktop_dir) -> list[str]:
        hits: list[str] = []
        if not desktop_dir.exists():
            return hits
        patterns = ["ipcRenderer", "require('fs')", "require('child_process')", "process."]
        for path in desktop_dir.rglob("*.tsx"):
            if path.name.endswith(".test.tsx"):
                continue
            in_block_comment = False
            text = self.read(path)
            for line_no, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("/*"):
                    in_block_comment = True
                if in_block_comment or stripped.startswith("//"):
                    if "*/" in stripped:
                        in_block_comment = False
                    continue
                if "*/" in stripped:
                    in_block_comment = False
                    continue
                for pattern in patterns:
                    if pattern in line:
                        rel = path.relative_to(self.project_dir)
                        hits.append(f"{rel}:{line_no}:{pattern}")
        return hits
