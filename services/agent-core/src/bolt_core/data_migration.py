"""M122 data migration readiness. Plan and audit only."""
from __future__ import annotations

from bolt_core.beta_reliability_common import BetaCheck, BetaReadinessBase, BetaReviewResult, check


class DataMigrationReadinessService(BetaReadinessBase):
    def review(self) -> BetaReviewResult:
        checks: list[BetaCheck] = []
        modules = [
            ("原始审计存储存在", "execution_audit_store"),
            ("上下文压缩存在", "context_compaction"),
            ("线程交接摘要存在", "thread_handoff_summary"),
            ("记忆权限边界存在", "memory_permission_boundary"),
            ("项目画像存在", "project_profile"),
            ("代码地图存在", "code_map_index"),
        ]
        for label, module in modules:
            path = self.src(module)
            checks.append(check(label, path.exists(), f"{path.name} {'存在' if path.exists() else '缺失'}"))

        plan = self.read(self.docs("release/data-migration-plan.md")).lower()
        required_terms = ["raw", "staging", "clean", "lineage"]
        lineage_ok = all(term in plan for term in required_terms)
        checks.append(check("迁移计划包含 raw/staging/clean/lineage", lineage_ok, "Context Lakehouse 层次和血缘需写清楚"))

        rollback_ok = "rollback" in plan and ("manual" in plan or "approval" in plan or "dry-run" in plan)
        checks.append(check("迁移计划包含人工回滚和演练", rollback_ok, "必须有 rollback 与 manual/approval/dry-run"))

        docs_ok = self.milestone_docs_complete(122)
        checks.append(check("M122 文档链完整", docs_ok, "exec plan / decision / review gate 已就位" if docs_ok else "M122 文档链缺失"))

        state = self.read(self.docs("project-state.md"))
        boundary_ok = "M122" in state and "未进入 M123" in state
        checks.append(check("M123 边界未越过", boundary_ok, "project-state 记录 M122 且未进入 M123"))

        no_auto_apply = "automatic migration" not in plan and "auto apply" not in plan
        checks.append(check("不会自动迁移数据", no_auto_apply, "迁移只能是计划、演练和人工审批", "blocking"))

        return BetaReviewResult(
            checks=checks[:8],
            next_step="等待爸爸复审 M122；迁移只给计划和风险，不自动改数据。",
        )
