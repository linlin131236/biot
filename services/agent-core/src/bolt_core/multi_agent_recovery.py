"""Multi-Agent Recovery. Classifies team failure scenarios and suggests
recovery steps. Never auto-retries dangerous actions. Requires human
confirmation for high risk scenarios.

Integrates with M64 FailureClassifier and M65 SafeRetry where useful.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class RecoveryScenario(str, Enum):
    PLANNER_BAD_SCOPE = "planner_bad_scope"
    RESEARCHER_MISSING_SOURCES = "researcher_missing_sources"
    BUILDER_TEST_FAILURE = "builder_test_failure"
    REVIEWER_BLOCKED = "reviewer_blocked"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    PERMISSION_WAITING = "permission_waiting"
    STALE_CONTEXT = "stale_context"
    UNKNOWN_FAILURE = "unknown_failure"

    @property
    def label_cn(self) -> str:
        return {
            "planner_bad_scope": "规划范围错误",
            "researcher_missing_sources": "研究员资料缺失",
            "builder_test_failure": "构建者测试失败",
            "reviewer_blocked": "审查者阻塞",
            "conflict_unresolved": "冲突未解决",
            "permission_waiting": "等待权限批准",
            "stale_context": "上下文过时",
            "unknown_failure": "未知失败",
        }.get(self.value, self.value)

    @property
    def responsible_role(self) -> str:
        _roles = {
            "planner_bad_scope": "planner",
            "researcher_missing_sources": "researcher",
            "builder_test_failure": "builder",
            "reviewer_blocked": "reviewer",
            "conflict_unresolved": "planner",
            "permission_waiting": "human",
            "stale_context": "planner",
            "unknown_failure": "planner",
        }
        return _roles.get(self.value, "planner")

    @property
    def risk_level(self) -> str:
        _risks = {
            "planner_bad_scope": "high",
            "researcher_missing_sources": "medium",
            "builder_test_failure": "medium",
            "reviewer_blocked": "high",
            "conflict_unresolved": "critical",
            "permission_waiting": "critical",
            "stale_context": "medium",
            "unknown_failure": "high",
        }
        return _risks.get(self.value, "high")


@dataclass
class RecoveryPlan:
    recovery_id: str
    scenario: RecoveryScenario
    scenario_label_cn: str
    responsible_role: str
    risk_level: str
    description_cn: str
    recovery_steps_cn: list[str]
    requires_human_confirmation: bool
    source_refs: list[str]
    created_at: str
    executed: bool

    def to_dict(self) -> dict:
        return {
            "recovery_id": self.recovery_id,
            "scenario": self.scenario.value,
            "scenario_label_cn": self.scenario_label_cn,
            "responsible_role": self.responsible_role,
            "risk_level": self.risk_level,
            "description_cn": self.description_cn,
            "recovery_steps_cn": self.recovery_steps_cn,
            "requires_human_confirmation": self.requires_human_confirmation,
            "source_refs": self.source_refs,
            "created_at": self.created_at,
            "executed": self.executed,
            "note": "此恢复计划为建议，不自动执行。高风险场景需人工确认。",
        }


# Recovery steps per scenario
_RECOVERY_STEPS: dict[RecoveryScenario, list[str]] = {
    RecoveryScenario.PLANNER_BAD_SCOPE: [
        "重新评估需求范围，确认是否有遗漏或过度设计",
        "检查决策记忆中是否有相关历史决策可供参考",
        "缩小范围到可验证的最小可行单元",
        "更新 Planner 输出，重新分配子任务",
    ],
    RecoveryScenario.RESEARCHER_MISSING_SOURCES: [
        "检查 BinCloud 知识索引是否有相关材料",
        "扩大搜索范围（限 2-4 篇新增资料）",
        "如果确实无资料，记录为证据缺失风险",
        "更新 ResearchSummary，标注资料缺失告警",
    ],
    RecoveryScenario.BUILDER_TEST_FAILURE: [
        "分析测试失败日志，定位失败原因",
        "检查是否因环境差异导致（依赖版本、系统差异）",
        "修复代码后重新运行 targeted tests",
        "如果同一测试反复失败 >= 2 次，触发 SkillLearner 分析",
    ],
    RecoveryScenario.REVIEWER_BLOCKED: [
        "查看审查者的阻塞原因和 P1/P2 问题",
        "构建者根据审查意见修复问题",
        "修复后重新提交 Builder 输出",
        "审查者重新评估（确保非同一上下文）",
        "注意：审查阻塞时不允许继续到 approved",
    ],
    RecoveryScenario.CONFLICT_UNRESOLVED: [
        "识别冲突类型和涉及角色",
        "如果涉及安全/PermissionGate/自动批准，立即升级为 critical",
        "生成 A/B/C 解决方案（参考 M86 ConflictResolution）",
        "等待人工决策，不可自动选择",
    ],
    RecoveryScenario.PERMISSION_WAITING: [
        "权限等待是正常流程，不自动批准",
        "如果等待超时（>30min），通知用户",
        "不绕过 PermissionGate，不自动降级权限",
        "如果权限被拒绝，记录原因并调整方案",
    ],
    RecoveryScenario.STALE_CONTEXT: [
        "重新运行 Context Compaction（M76）",
        "重新生成 Thread Handoff Summary（M77）",
        "检查 git 状态是否有未提交变更",
        "如果上下文过期超过 1 小时，建议重新建立会话",
    ],
    RecoveryScenario.UNKNOWN_FAILURE: [
        "收集所有相关日志和状态信息",
        "检查 M64 FailureClassifier 是否能分类",
        "如果无法自动分类，升级为人工处理",
        "记录为已知未知风险，后续补充恢复策略",
    ],
}


class MultiAgentRecoveryService:
    """Classifies team failures and suggests recovery plans.
    Never auto-retries dangerous tools."""

    def __init__(self) -> None:
        self._plans: dict[str, RecoveryPlan] = {}

    def classify_and_suggest(
        self,
        scenario: str,
        description_cn: str,
        source_refs: list[str] | None = None,
    ) -> RecoveryPlan:
        """Classify a team failure and generate a recovery plan."""
        try:
            sc = RecoveryScenario(scenario)
        except ValueError:
            sc = RecoveryScenario.UNKNOWN_FAILURE

        steps = _RECOVERY_STEPS.get(sc, _RECOVERY_STEPS[RecoveryScenario.UNKNOWN_FAILURE])
        is_high_risk = sc.risk_level in ("high", "critical")

        plan = RecoveryPlan(
            recovery_id=f"rec-{uuid.uuid4().hex[:8]}",
            scenario=sc,
            scenario_label_cn=sc.label_cn,
            responsible_role=sc.responsible_role,
            risk_level=sc.risk_level,
            description_cn=description_cn,
            recovery_steps_cn=steps,
            requires_human_confirmation=is_high_risk,
            source_refs=source_refs or [],
            created_at=datetime.now(timezone.utc).isoformat(),
            executed=False,
        )
        self._plans[plan.recovery_id] = plan
        return plan

    def get_plan(self, recovery_id: str) -> Optional[RecoveryPlan]:
        return self._plans.get(recovery_id)

    def list_plans(self) -> list[RecoveryPlan]:
        return list(self._plans.values())

    def scenario_options(self) -> list[dict]:
        """List all valid scenarios with Chinese labels."""
        return [
            {
                "scenario": s.value,
                "label_cn": s.label_cn,
                "responsible_role": s.responsible_role,
                "risk_level": s.risk_level,
            }
            for s in RecoveryScenario
        ]
