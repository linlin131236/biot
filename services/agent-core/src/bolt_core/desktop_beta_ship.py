"""M171-M180 desktop beta ship readiness gate.

Read-only checks only. This service never runs packaging, publishing, git, or
installer commands; it only verifies that the release-candidate surface exists.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bolt_core.beta_reliability_common import BetaCheck, BetaReadinessBase, BetaReviewResult, check


@dataclass
class DesktopBetaShipResult(BetaReviewResult):
    ready: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.ready = self.all_passed

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["ready"] = self.ready
        return data


class DesktopBetaShipService(BetaReadinessBase):
    """Aggregate the final desktop Beta readiness checks for M171-M180."""

    def review(self) -> DesktopBetaShipResult:
        checks = [
            self._m171_package_smoke(),
            self._m172_first_run_setup(),
            self._m173_task_flow(),
            self._m174_error_states(),
            self._m175_settings_ready(),
            self._m176_audit_recovery(),
            self._m177_performance_signals(),
            self._m178_installer_readiness(),
            self._m179_dogfood_evidence(),
            self._m180_docs_gate(),
        ]
        return DesktopBetaShipResult(
            checks=checks,
            next_step="M180 通过后只允许人工复审；不自动 release/tag/delete/push。",
        )

    def _m171_package_smoke(self) -> BetaCheck:
        scripts = self._desktop_scripts()
        ok = all(name in scripts for name in ["build", "package:win", "package:win:dir"]) and self.exists("scripts/check-desktop-package-runtime.mjs")
        detail = "桌面 build、Windows package 和 package runtime smoke 脚本存在" if ok else "缺少 build/package/package-runtime smoke 脚本"
        return check("M171 桌面打包 smoke 就绪", ok, detail)

    def _m172_first_run_setup(self) -> BetaCheck:
        files = [
            "apps/desktop/src/LiquidGlassWorkbench.tsx",
            "apps/desktop/src/LiquidGlassSettings.tsx",
            "apps/desktop/src/PermissionCenterPanel.tsx",
        ]
        ok = all(self.exists(path) for path in files)
        return check("M172 首次启动引导就绪", ok, "工作区、设置、权限中心入口存在" if ok else "缺少首次启动核心入口")

    def _m173_task_flow(self) -> BetaCheck:
        files = [
            "apps/desktop/src/PatchPreviewPanel.tsx",
            "apps/desktop/src/TestRunnerPanel.tsx",
            "apps/desktop/src/TaskResultSummaryPanel.tsx",
            "apps/desktop/src/dogfoodSmoke.test.ts",
        ]
        ok = all(self.exists(path) for path in files)
        return check("M173 真实任务主流程就绪", ok, "补丁预览、安全测试、结果摘要和 dogfood smoke 已接入" if ok else "任务主流程缺少关键桌面入口")

    def _m174_error_states(self) -> BetaCheck:
        diagnostics = self.project_dir / "apps/desktop/src/DiagnosticsCenterPanel.tsx"
        text = self.read(diagnostics)
        ok = diagnostics.exists() and any(term in text for term in ["连接失败", "模型失败", "诊断"])
        return check("M174 错误态体验就绪", ok, "诊断中心包含中文错误态信号" if ok else "诊断中心缺少清晰错误态")

    def _m175_settings_ready(self) -> BetaCheck:
        files = [
            "services/agent-core/src/bolt_core/desktop_settings.py",
            "services/agent-core/src/bolt_core/desktop_settings_api.py",
            "apps/desktop/src/LiquidGlassSettings.tsx",
        ]
        ok = all(self.exists(path) for path in files)
        return check("M175 设置持久化就绪", ok, "设置服务、API 和桌面设置页存在" if ok else "设置持久化链路不完整")

    def _m176_audit_recovery(self) -> BetaCheck:
        files = [
            "apps/desktop/src/AuditTimelinePanel.tsx",
            "apps/desktop/src/SessionRecoveryPanel.tsx",
            "services/agent-core/src/bolt_core/release_readiness.py",
        ]
        ok = all(self.exists(path) for path in files)
        return check("M176 审计与恢复可视化就绪", ok, "审计时间线、会话恢复和发布准备度存在" if ok else "审计/恢复链路不完整")

    def _m177_performance_signals(self) -> BetaCheck:
        package_root = self.project_dir / "package.json"
        desktop_tests = list((self.project_dir / "apps/desktop/src").glob("*.test.ts*"))
        package_text = self.read(package_root)
        ok = "quality" in package_text and len(desktop_tests) >= 10
        return check("M177 性能与质量信号就绪", ok, "质量门和桌面测试基线存在" if ok else "缺少质量门或桌面测试基线")

    def _m178_installer_readiness(self) -> BetaCheck:
        scripts = self._desktop_scripts()
        joined = " ".join(str(value) for value in scripts.values())
        ok = "package:win" in scripts and "package:win:nsis" in scripts and "--publish never" in joined
        return check("M178 安装包发布前检查就绪", ok, "Windows 安装包脚本存在且 publish=never" if ok else "安装包脚本缺失或可能自动发布")

    def _m179_dogfood_evidence(self) -> BetaCheck:
        files = [
            "apps/desktop/src/dogfoodSmoke.test.ts",
            "apps/desktop/src/uiWorkflowDogfood.test.tsx",
            "docs/release/dogfood-smoke.md",
        ]
        ok = all(self.exists(path) for path in files)
        return check("M179 真实 dogfood 证据就绪", ok, "桌面 dogfood 测试与发布 dogfood 文档存在" if ok else "缺少 dogfood 证据")

    def _m180_docs_gate(self) -> BetaCheck:
        missing = self.docs_missing(171, 180)
        state = self.read(self.docs("project-state.md"))
        state_ok = "M180" in state and "release/tag/delete" in state
        ok = not missing and state_ok
        detail = "M171-M180 文档链完整，project-state 已写明 M180 状态" if ok else "缺失: " + ", ".join(missing or ["project-state M180 状态"])
        return check("M180 Beta Release Candidate Gate 就绪", ok, detail)

    def _desktop_scripts(self) -> dict[str, str]:
        package_json = self.project_dir / "apps/desktop/package.json"
        try:
            data = json.loads(self.read(package_json) or "{}")
        except json.JSONDecodeError:
            return {}
        scripts = data.get("scripts", {})
        return scripts if isinstance(scripts, dict) else {}
