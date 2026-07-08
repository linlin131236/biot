"""M121 crash recovery readiness. Read-only assessment only."""
from __future__ import annotations

from bolt_core.beta_reliability_common import BetaCheck, BetaReadinessBase, BetaReviewResult, check


class CrashRecoveryService(BetaReadinessBase):
    def review(self) -> BetaReviewResult:
        checks: list[BetaCheck] = []

        required_modules = [
            ("检查点服务存在", "checkpoint"),
            ("暂停恢复服务存在", "pause_resume"),
            ("会话恢复入口存在", "session_recovery_api"),
            ("审计完整性检查存在", "execution_audit_integrity"),
            ("线程接手摘要存在", "thread_handoff_summary"),
            ("长任务恢复复盘存在", "long_task_recovery_dogfood"),
        ]
        for label, module in required_modules:
            path = self.src(module)
            checks.append(check(label, path.exists(), f"{path.name} {'存在' if path.exists() else '缺失'}"))

        docs_ok = self.milestone_docs_complete(121)
        checks.append(check("M121 文档链完整", docs_ok, "exec plan / decision / review gate 已就位" if docs_ok else "M121 文档链缺失"))

        state = self.read(self.docs("project-state.md"))
        boundary_ok = ("M121" in state and "未进入 M122" in state) or ("M125" in state and "未进入 M126" in state)
        checks.append(check("M122 边界未越过", boundary_ok, "project-state 记录 M121 未进入 M122，或最终状态未进入 M126"))

        return BetaReviewResult(
            checks=checks,
            next_step="等待用户复审 M121；恢复能力只做检查，不执行任何恢复动作。",
        )
