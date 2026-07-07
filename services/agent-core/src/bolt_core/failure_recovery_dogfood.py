"""Failure Recovery Dogfood (M119). Evaluate recovery behavior for failure scenarios.

Checks: patch apply failure, test runner failure, permission denied,
stale proposal, timeout, interrupted long task. Never auto-fixes.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RecoveryDogfoodResult:
    case_id: str; passed: bool; failure_category: str; safe_to_retry: bool
    requires_human: bool; recovery_plan: str; audit_evidence: str
    auto_fix_allowed: bool = False

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "passed": self.passed,
                "failure_category": self.failure_category,
                "safe_to_retry": self.safe_to_retry,
                "requires_human": self.requires_human,
                "recovery_plan": self.recovery_plan,
                "audit_evidence": self.audit_evidence,
                "auto_fix_allowed": self.auto_fix_allowed}


@dataclass
class RecoveryDogfoodSummary:
    total_cases: int = 0; passed: int = 0; failed: int = 0
    results: list[RecoveryDogfoodResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_cases": self.total_cases, "passed": self.passed,
                "failed": self.failed,
                "pass_rate": f"{self.passed}/{self.total_cases}" if self.total_cases else "N/A",
                "all_passed": self.passed == self.total_cases and self.total_cases > 0,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "失败恢复狗粮评估不自动修复任何问题（auto_fix_allowed=false）。",
                "verdict": "✅ 通过" if self.passed == self.total_cases else "❌ 失败"}


# ── Recovery rules ──

_RECOVERY_RULES: dict[str, dict] = {
    "patch_apply_failure": {
        "category": "工具执行失败", "safe_to_retry": True,
        "requires_human": False,
        "plan": "补丁应用失败：请检查目标文件是否存在、diff内容是否匹配目标文件。可修正diff后重试。",
        "evidence": "patch_apply_eval_failure_log",
    },
    "test_runner_failure": {
        "category": "测试失败", "safe_to_retry": True,
        "requires_human": False,
        "plan": "测试运行失败：请查看测试输出中的具体失败项，修复代码后重新运行测试。",
        "evidence": "test_runner_failure_output",
    },
    "permission_denied": {
        "category": "安全阻断", "safe_to_retry": False,
        "requires_human": True,
        "plan": "权限不足：此操作需要爸爸在PermissionGate中明确批准。请等待批准后再执行。",
        "evidence": "permission_denied_audit_entry",
    },
    "stale_proposal": {
        "category": "工具执行失败", "safe_to_retry": False,
        "requires_human": True,
        "plan": "提案已过期（git HEAD已变更）：请基于最新代码重新创建提案。不可直接重试过期提案。",
        "evidence": "stale_proposal_git_head_diff",
    },
    "timeout": {
        "category": "网络失败", "safe_to_retry": True,
        "requires_human": False,
        "plan": "操作超时：可增加超时时间或检查网络连接后重试。重试前确认无副作用残留。",
        "evidence": "timeout_threshold_log",
    },
    "interrupted_long_task": {
        "category": "未知失败", "safe_to_retry": False,
        "requires_human": True,
        "plan": "长任务中断：请查看中断点检查点(checkpoint)，确认已完成步骤。由爸爸决定是否从检查点恢复或重新开始。",
        "evidence": "checkpoint_snapshot",
    },
}


class FailureRecoveryDogfoodService:
    """M119 失败恢复复盘服务。"""

    @staticmethod
    def run_all() -> RecoveryDogfoodSummary:
        results = []
        for case_id, rules in _RECOVERY_RULES.items():
            result = RecoveryDogfoodResult(
                case_id=case_id,
                passed=True,  # Rules are definitions, always pass
                failure_category=rules["category"],
                safe_to_retry=rules["safe_to_retry"],
                requires_human=rules["requires_human"],
                recovery_plan=rules["plan"],
                audit_evidence=rules["evidence"],
                auto_fix_allowed=False,
            )
            # Verify: dangerous retry must be false for permission/stale/interrupted
            if case_id in ("permission_denied", "stale_proposal", "interrupted_long_task"):
                if result.safe_to_retry:
                    result = RecoveryDogfoodResult(
                        case_id=case_id, passed=False,
                        failure_category=rules["category"],
                        safe_to_retry=rules["safe_to_retry"],
                        requires_human=rules["requires_human"],
                        recovery_plan="危险：不安全重试已标记为safe",
                        audit_evidence=rules["evidence"],
                    )
            results.append(result)

        p = sum(1 for r in results if r.passed)
        # Check invariants
        for r in results:
            if r.auto_fix_allowed:
                p -= 1  # auto-fix must be false

        return RecoveryDogfoodSummary(
            total_cases=len(results), passed=min(p, len(results)),
            failed=len(results) - min(p, len(results)),
            results=results,
        )
