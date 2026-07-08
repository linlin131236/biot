"""M125 public beta readiness. Final read-only gate."""
from __future__ import annotations

from dataclasses import dataclass

from bolt_core.beta_reliability_common import BetaCheck, BetaReadinessBase, BetaReviewResult, check
from bolt_core.crash_recovery import CrashRecoveryService
from bolt_core.data_migration import DataMigrationReadinessService
from bolt_core.privacy_security_audit import PrivacySecurityAuditService
from bolt_core.update_rollback import UpdateRollbackReadinessService


@dataclass
class PublicBetaReviewResult(BetaReviewResult):
    beta_allowed: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.beta_allowed = self.all_passed

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["beta_allowed"] = self.beta_allowed
        return data


class PublicBetaReadinessService(BetaReadinessBase):
    def review(self) -> PublicBetaReviewResult:
        checks: list[BetaCheck] = []

        required_reviews = [
            ("M121 崩溃恢复门禁通过", CrashRecoveryService(str(self.project_dir))),
            ("M122 数据迁移门禁通过", DataMigrationReadinessService(str(self.project_dir))),
            ("M123 升级回滚门禁通过", UpdateRollbackReadinessService(str(self.project_dir))),
            ("M124 隐私安全审计通过", PrivacySecurityAuditService(str(self.project_dir))),
        ]
        for label, service in required_reviews:
            result = service.review()
            detail = "通过" if result.all_passed else "失败: " + ", ".join(result.p1_failures)
            checks.append(check(label, result.all_passed, detail))

        history_modules = ["desktop_beta_dogfood", "tool_ecosystem_dogfood", "agent_intelligence_dogfood"]
        history_ok = all(self.src(module).exists() for module in history_modules)
        checks.append(check("M100/M110/M120 历史复盘仍存在", history_ok, "桌面、工具生态、智能复盘三条基线需保留"))

        v8_files = [
            self.src("crash_recovery"),
            self.src("data_migration"),
            self.src("update_rollback"),
            self.src("privacy_security_audit"),
            self.src("public_beta_readiness"),
        ]
        no_auto_hits = self.scan_files(v8_files, ["sub" + "process.run", "os." + "system", "shutil." + "rmtree", "git." + "push("])
        checks.append(check("无自动 push/release/tag/delete", not no_auto_hits, "; ".join(no_auto_hits[:5]) if no_auto_hits else "未发现自动危险操作"))

        missing_docs = self.docs_missing(121, 125)
        docs_name = "M121-M125 文档链完整" if not missing_docs else "M121-M125 文档链完整（缺失: " + ", ".join(missing_docs) + "）"
        checks.append(check(docs_name, not missing_docs, "全部就位" if not missing_docs else "缺失: " + ", ".join(missing_docs)))

        handoff = self.docs("final-handoff/m125-beta-handoff.md")
        checks.append(check("最终接手包存在", handoff.exists(), f"{handoff.name} {'存在' if handoff.exists() else '缺失'}"))

        state = self.read(self.docs("project-state.md"))
        push_state_ok = "未 push" in state or ("已 push" in state and "origin/main" in state)
        state_ok = "M125" in state and push_state_ok and "未进入 M126" in state
        checks.append(check("project-state 标记 M125 状态准确", state_ok, "project-state 需写明 M125、未进入 M126，并标明未 push 或已 push 同步"))

        m126_files = list((self.project_dir / "docs/exec-plans/active").glob("126-*.md"))
        checks.append(check("未进入 M126", not m126_files, "未发现 M126 文档" if not m126_files else f"发现 {len(m126_files)} 个 M126 文档"))

        return PublicBetaReviewResult(
            checks=checks,
            next_step="M125 完成后停止，等待用户复审；不自动 push、release、tag、delete。",
        )
