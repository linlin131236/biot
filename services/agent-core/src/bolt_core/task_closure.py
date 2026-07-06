"""Task Closure model: structured evidence for real agent task completion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from bolt_core.goal import GoalStatus


class TaskTemplateId(str):
    BUGFIX = "bugfix"
    DOCS = "docs"
    TEST = "test"
    QUALITY = "quality"
    REVIEW = "review"


class TaskClosureStatus(str):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_PERMISSION = "waiting_permission"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


# Legal state transitions (finite state machine)
_TRANSITIONS: dict[TaskClosureStatus, set[TaskClosureStatus]] = {
    TaskClosureStatus.PENDING: {TaskClosureStatus.PLANNING},
    TaskClosureStatus.PLANNING: {TaskClosureStatus.EXECUTING},
    TaskClosureStatus.EXECUTING: {
        TaskClosureStatus.WAITING_PERMISSION,
        TaskClosureStatus.VERIFYING,
        TaskClosureStatus.FAILED,
    },
    TaskClosureStatus.WAITING_PERMISSION: {TaskClosureStatus.EXECUTING},
    TaskClosureStatus.VERIFYING: {
        TaskClosureStatus.COMPLETED,
        TaskClosureStatus.REPAIRING,
        TaskClosureStatus.REVIEWING,
        TaskClosureStatus.FAILED,
    },
    TaskClosureStatus.REPAIRING: {
        TaskClosureStatus.EXECUTING,
        TaskClosureStatus.FAILED,
        TaskClosureStatus.STOPPED,
    },
    TaskClosureStatus.REVIEWING: {
        TaskClosureStatus.COMPLETED,
        TaskClosureStatus.FAILED,
    },
}

# Any status can go to STOPPED (user explicit stop)
_ALL_STATUSES = [
    TaskClosureStatus.PENDING, TaskClosureStatus.PLANNING,
    TaskClosureStatus.EXECUTING, TaskClosureStatus.WAITING_PERMISSION,
    TaskClosureStatus.VERIFYING, TaskClosureStatus.REPAIRING,
    TaskClosureStatus.REVIEWING, TaskClosureStatus.COMPLETED,
    TaskClosureStatus.FAILED,
]


@dataclass
class TaskClosure:
    id: str
    objective: str = ""
    template_id: TaskTemplateId = TaskTemplateId.BUGFIX
    run_id: Optional[str] = None
    goal_id: Optional[str] = None
    status: TaskClosureStatus = TaskClosureStatus.PENDING
    plan_summary: str = ""
    changed_files: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    command_results: list[str] = field(default_factory=list)
    permission_request_ids: list[str] = field(default_factory=list)
    retry_count: int = 0
    review_summary: str = ""
    next_action: str = ""
    created_at: float = 0.0


MAX_RETRIES = 3


def can_transition(current: TaskClosureStatus, target: TaskClosureStatus) -> bool:
    """Check if a state transition is legal."""
    allowed = _TRANSITIONS.get(current)
    if allowed is None:
        return target == TaskClosureStatus.STOPPED
    return target in allowed or target == TaskClosureStatus.STOPPED


def task_templates() -> list[dict]:
    """Return task templates with Chinese labels (backend gives structure, frontend displays)."""
    return [
        {"id": TaskTemplateId.BUGFIX, "label": "修复小问题", "description": "定位并修复代码缺陷", "default_checks": ["lint", "test"]},
        {"id": TaskTemplateId.DOCS, "label": "更新文档", "description": "添加或修正文档内容", "default_checks": ["lint:docs"]},
        {"id": TaskTemplateId.TEST, "label": "增加测试", "description": "为现有代码补充测试", "default_checks": ["test", "coverage"]},
        {"id": TaskTemplateId.QUALITY, "label": "跑质量门", "description": "运行 lint/build/test 验证", "default_checks": ["quality"]},
        {"id": TaskTemplateId.REVIEW, "label": "生成审查摘要", "description": "汇总变更和验证结果", "default_checks": ["review"]},
    ]
