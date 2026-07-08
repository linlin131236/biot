"""Product Workbench (M126).

Read-only desktop workflow summary for the practical agent loop:
user intent -> plan -> read context -> patch preview -> human approval
-> apply -> tests -> audit/recovery.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class WorkbenchStage:
    stage_id: str
    label_cn: str
    status: str
    detail_cn: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "label_cn": self.label_cn,
            "status": self.status,
            "detail_cn": self.detail_cn,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class WorkbenchLane:
    lane_id: str
    label_cn: str
    status: str
    detail_cn: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lane_id": self.lane_id,
            "label_cn": self.label_cn,
            "status": self.status,
            "detail_cn": self.detail_cn,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class WorkbenchSafety:
    auto_apply_allowed: bool
    auto_approve_allowed: bool
    human_approval_required: bool
    dangerous_operations_blocked: bool
    summary_cn: str

    def to_dict(self) -> dict:
        return {
            "auto_apply_allowed": self.auto_apply_allowed,
            "auto_approve_allowed": self.auto_approve_allowed,
            "human_approval_required": self.human_approval_required,
            "dangerous_operations_blocked": self.dangerous_operations_blocked,
            "summary_cn": self.summary_cn,
        }


@dataclass(frozen=True)
class WorkbenchCheck:
    check_id: str
    label_cn: str
    required: bool
    status: str

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "label_cn": self.label_cn,
            "required": self.required,
            "status": self.status,
        }


@dataclass(frozen=True)
class PatchApprovalSummary:
    label_cn: str
    warning_cn: str
    checks: list[WorkbenchCheck]

    def to_dict(self) -> dict:
        return {
            "label_cn": self.label_cn,
            "warning_cn": self.warning_cn,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class TestCommandSummary:
    test_id: str
    label_cn: str
    status: str

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "label_cn": self.label_cn,
            "status": self.status,
        }


@dataclass(frozen=True)
class TestFeedbackSummary:
    label_cn: str
    warning_cn: str
    arbitrary_shell_allowed: bool
    commands: list[TestCommandSummary]

    def to_dict(self) -> dict:
        return {
            "label_cn": self.label_cn,
            "warning_cn": self.warning_cn,
            "arbitrary_shell_allowed": self.arbitrary_shell_allowed,
            "commands": [command.to_dict() for command in self.commands],
        }


@dataclass(frozen=True)
class FailureRecoverySummary:
    label_cn: str
    warning_cn: str
    auto_retry_allowed: bool
    auto_resume_allowed: bool
    checks: list[WorkbenchCheck]

    def to_dict(self) -> dict:
        return {
            "label_cn": self.label_cn,
            "warning_cn": self.warning_cn,
            "auto_retry_allowed": self.auto_retry_allowed,
            "auto_resume_allowed": self.auto_resume_allowed,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class WorkbenchSnapshot:
    summary_cn: str
    read_only: bool
    current_stage_id: str
    stages: list[WorkbenchStage]
    lanes: list[WorkbenchLane]
    safety: WorkbenchSafety
    patch_approval: PatchApprovalSummary
    test_feedback: TestFeedbackSummary
    failure_recovery: FailureRecoverySummary
    next_actions: list[str]
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "summary_cn": self.summary_cn,
            "read_only": self.read_only,
            "current_stage_id": self.current_stage_id,
            "stages": [stage.to_dict() for stage in self.stages],
            "lanes": [lane.to_dict() for lane in self.lanes],
            "safety": self.safety.to_dict(),
            "patch_approval": self.patch_approval.to_dict(),
            "test_feedback": self.test_feedback.to_dict(),
            "failure_recovery": self.failure_recovery.to_dict(),
            "next_actions": self.next_actions,
            "updated_at": self.updated_at,
        }


class ProductWorkbenchService:
    """Builds a read-only product workflow snapshot for the desktop."""

    def __init__(self, project_dir: str | Path | None = None) -> None:
        candidate = Path(project_dir).resolve() if project_dir is not None else Path(__file__).resolve().parents[4]
        self._project_dir = self._resolve_project_dir(candidate)

    def snapshot(self) -> WorkbenchSnapshot:
        return WorkbenchSnapshot(
            summary_cn="从一句话需求到补丁验证的 Agent 工作台：看目标、看补丁、看批准、看测试、看恢复。",
            read_only=True,
            current_stage_id="user_intent",
            stages=self._stages(),
            lanes=self._lanes(),
            safety=WorkbenchSafety(
                auto_apply_allowed=False,
                auto_approve_allowed=False,
                human_approval_required=True,
                dangerous_operations_blocked=True,
                summary_cn="工作台只读展示；写入、apply、测试执行和恢复动作必须走权限边界，由爸爸人工批准。",
            ),
            patch_approval=self._patch_approval(),
            test_feedback=self._test_feedback(),
            failure_recovery=self._failure_recovery(),
            next_actions=[
                "先在目标区确认一句话任务是否明确。",
                "写入前查看补丁预览和风险标签。",
                "批准后再查看测试结果、审计记录和恢复建议。",
            ],
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _failure_recovery(self) -> FailureRecoverySummary:
        return FailureRecoverySummary(
            label_cn="失败与恢复检查",
            warning_cn="这里只解释失败和恢复前条件；不自动 retry，不自动 resume。",
            auto_retry_allowed=False,
            auto_resume_allowed=False,
            checks=[
                WorkbenchCheck("failure_classified", "失败必须先分类并说明原因", True, "ready"),
                WorkbenchCheck("retry_risk_reviewed", "重试风险必须先评估", True, "ready"),
                WorkbenchCheck("permission_reverified", "恢复前必须重新验证权限", True, "ready"),
                WorkbenchCheck("state_reverified", "恢复前必须重新验证状态", True, "ready"),
                WorkbenchCheck("manual_resume_required", "恢复必须由爸爸人工确认", True, "blocked"),
            ],
        )

    def _test_feedback(self) -> TestFeedbackSummary:
        return TestFeedbackSummary(
            label_cn="白名单测试回填",
            warning_cn="这里只展示允许的测试入口和结果摘要；不允许输入任意 shell 命令。",
            arbitrary_shell_allowed=False,
            commands=[
                TestCommandSummary("backend_unit", "后端单元测试", "ready"),
                TestCommandSummary("backend_api", "后端 API 测试", "ready"),
                TestCommandSummary("shared_test", "共享模块测试", "ready"),
                TestCommandSummary("desktop_test", "桌面端测试", "ready"),
                TestCommandSummary("desktop_build", "桌面端构建", "ready"),
                TestCommandSummary("quality_gate", "全量质量门", "ready"),
            ],
        )

    def _stages(self) -> list[WorkbenchStage]:
        return [
            self._stage("user_intent", "用户意图", "active", "等待爸爸输入或确认任务目标。", ["apps/desktop/src/TaskHomePanel.tsx"]),
            self._stage("plan", "计划拆解", "ready", "任务进入执行前必须有计划、验收标准和风险边界。", ["services/agent-core/src/bolt_core/planner_task_graph.py"]),
            self._stage("read_context", "读取上下文", "ready", "只读读取项目资料、代码地图、记忆和审计摘要。", ["services/agent-core/src/bolt_core/code_map_index.py"]),
            self._stage("patch_preview", "补丁预览", self._exists_status("apps/desktop/src/PatchPreviewPanel.tsx"), "补丁先预览，不直接写入真实文件。", ["apps/desktop/src/PatchPreviewPanel.tsx"]),
            self._stage("human_approval", "人工批准", "blocked", "写入和执行前必须由爸爸批准，Agent 不能自批。", ["services/agent-core/src/bolt_core/approval_apply.py"]),
            self._stage("apply_patch", "应用补丁", "ready", "批准后才可进入门控 apply；delete/push/release/tag 不在自动范围内。", ["services/agent-core/src/bolt_core/approval_apply.py"]),
            self._stage("run_tests", "测试验证", "ready", "只允许白名单测试命令，并回填结构化结果。", ["services/agent-core/src/bolt_core/test_runner_integration.py"]),
            self._stage("audit_and_recovery", "审计与恢复", "ready", "失败先解释、再恢复建议，不自动 retry 或 fix。", ["services/agent-core/src/bolt_core/session_recovery_api.py"]),
        ]

    def _patch_approval(self) -> PatchApprovalSummary:
        return PatchApprovalSummary(
            label_cn="补丁批准检查",
            warning_cn="这里不会自动批准；所有写入都必须由爸爸看过补丁、确认范围后批准。",
            checks=[
                WorkbenchCheck("preview_required", "必须先查看补丁预览", True, "ready"),
                WorkbenchCheck("target_scope_locked", "目标文件范围必须和 diff 完全匹配", True, "ready"),
                WorkbenchCheck("human_approval_required", "必须由爸爸人工批准", True, "blocked"),
                WorkbenchCheck("stale_recheck_required", "apply 前必须复查提案是否过期", True, "ready"),
                WorkbenchCheck("audit_required", "成功或失败都必须留下审计记录", True, "ready"),
            ],
        )

    def _lanes(self) -> list[WorkbenchLane]:
        return [
            self._lane("patch", "补丁预览", self._exists_status("services/agent-core/src/bolt_core/patch_proposal.py"), "展示补丁、文件范围、风险和 diff。", ["services/agent-core/src/bolt_core/patch_proposal.py"]),
            self._lane("test", "测试回填", self._exists_status("services/agent-core/src/bolt_core/test_runner_integration.py"), "展示白名单测试结果和摘要。", ["services/agent-core/src/bolt_core/test_runner_integration.py"]),
            self._lane("failure", "失败解释", self._exists_status("apps/desktop/src/FailureExplanationPanel.tsx"), "把失败分类成中文原因、影响和建议。", ["apps/desktop/src/FailureExplanationPanel.tsx"]),
            self._lane("recovery", "恢复建议", self._exists_status("apps/desktop/src/SessionRecoveryPanel.tsx"), "只展示可恢复任务和恢复前检查。", ["apps/desktop/src/SessionRecoveryPanel.tsx"]),
        ]

    def _stage(self, stage_id: str, label_cn: str, status: str, detail_cn: str, evidence: list[str]) -> WorkbenchStage:
        return WorkbenchStage(stage_id, label_cn, status, detail_cn, evidence)

    def _lane(self, lane_id: str, label_cn: str, status: str, detail_cn: str, evidence: list[str]) -> WorkbenchLane:
        return WorkbenchLane(lane_id, label_cn, status, detail_cn, evidence)

    def _exists_status(self, rel: str) -> str:
        return "ready" if (self._project_dir / rel).exists() else "empty"

    @staticmethod
    def _resolve_project_dir(candidate: Path) -> Path:
        current = candidate.resolve()
        for path in [current, *current.parents]:
            if (path / "docs").is_dir() and (path / "apps").is_dir() and (path / "services").is_dir():
                return path
        return current
