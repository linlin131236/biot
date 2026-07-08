"""M123 update and rollback readiness. Read-only assessment only."""
from __future__ import annotations

from bolt_core.beta_reliability_common import BetaCheck, BetaReadinessBase, BetaReviewResult, check


class UpdateRollbackReadinessService(BetaReadinessBase):
    def review(self) -> BetaReviewResult:
        checks: list[BetaCheck] = []
        modules = [
            ("发布准备门禁存在", "release_readiness"),
            ("本地发布清单存在", "local_release_checklist"),
            ("恢复策略存在", "recovery_policy"),
            ("批准写入边界存在", "approval_apply"),
            ("安全测试运行器存在", "test_runner_integration"),
        ]
        for label, module in modules:
            path = self.src(module)
            checks.append(check(label, path.exists(), f"{path.name} {'存在' if path.exists() else '缺失'}"))

        plan = self.read(self.docs("release/update-rollback-plan.md")).lower()
        plan_ok = all(term in plan for term in ["manual", "update", "rollback", "approval"])
        checks.append(check("升级回滚计划要求人工批准", plan_ok, "计划必须写明 manual/update/rollback/approval"))

        auto_release_blocked = "automatic release" not in plan and "auto release" not in plan
        checks.append(check("禁止自动发布", auto_release_blocked, "计划中不得出现 automatic release/auto release"))

        docs_ok = self.milestone_docs_complete(123)
        checks.append(check("M123 文档链完整", docs_ok, "exec plan / decision / review gate 已就位" if docs_ok else "M123 文档链缺失"))

        state = self.read(self.docs("project-state.md"))
        boundary_ok = ("M123" in state and "未进入 M124" in state) or ("M125" in state and "未进入 M126" in state)
        checks.append(check("M124 边界未越过", boundary_ok, "project-state 记录 M123 未进入 M124，或最终状态未进入 M126"))

        return BetaReviewResult(
            checks=checks,
            next_step="等待用户复审 M123；升级、回滚和发布都必须人工触发。",
        )
