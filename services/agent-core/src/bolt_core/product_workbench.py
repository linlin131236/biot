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
class WorkbenchSnapshot:
    summary_cn: str
    read_only: bool
    current_stage_id: str
    stages: list[WorkbenchStage]
    lanes: list[WorkbenchLane]
    safety: WorkbenchSafety
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
            "next_actions": self.next_actions,
            "updated_at": self.updated_at,
        }


class ProductWorkbenchService:
    """Builds a read-only product workflow snapshot for the desktop."""

    def __init__(self, project_dir: str | Path | None = None) -> None:
        self._project_dir = Path(project_dir) if project_dir is not None else Path(__file__).resolve().parents[4]

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
            next_actions=[
                "先在目标区确认一句话任务是否明确。",
                "写入前查看补丁预览和风险标签。",
                "批准后再查看测试结果、审计记录和恢复建议。",
            ],
            updated_at=datetime.now(timezone.utc).isoformat(),
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
