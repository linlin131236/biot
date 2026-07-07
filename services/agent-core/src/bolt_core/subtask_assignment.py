"""Subtask Assignment. Planner creates structured tasks for Builder/
Researcher/Reviewer with dependencies, risk levels, and role compatibility checks.

Never auto-executes. Never bypasses PermissionGate for dangerous assignments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


# ── Statuses ────────────────────────────────────────────────────────────

class SubtaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def label_cn(self) -> str:
        _labels = {
            "pending": "待办",
            "ready": "就绪",
            "in_progress": "进行中",
            "blocked": "阻塞",
            "awaiting_review": "待审查",
            "completed": "已完成",
            "failed": "已失败",
        }
        return _labels.get(self.value, self.value)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def label_cn(self) -> str:
        _labels = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}
        return _labels.get(self.value, self.value)

    @property
    def requires_human(self) -> bool:
        return self in (RiskLevel.HIGH, RiskLevel.CRITICAL)


# ── Role compatibility ──────────────────────────────────────────────────

# Which roles can be assigned which task types
_ROLE_ACTIONS: dict[str, dict[str, bool]] = {
    "planner":    {"plan": True,  "research": False, "build": False, "review": False},
    "researcher": {"plan": False, "research": True,  "build": False, "review": False},
    "builder":    {"plan": False, "research": False, "build": True,  "review": False},
    "reviewer":   {"plan": False, "research": False, "build": False, "review": True},
    "skill_learner": {"plan": False, "research": False, "build": False, "review": False},
}

_DANGEROUS_ROLES = {"builder": ["write", "execute", "commit"]}


# ── Data ────────────────────────────────────────────────────────────────

@dataclass
class SubtaskAssignment:
    task_id: str
    title_cn: str
    description_cn: str
    assigned_role: str
    task_type: str  # plan / research / build / review
    status: SubtaskStatus
    dependencies: list[str]  # task_ids this depends on
    risk_level: RiskLevel
    required_evidence: list[str]
    source_refs: list[str]
    requires_human_confirmation: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title_cn": self.title_cn,
            "description_cn": self.description_cn,
            "assigned_role": self.assigned_role,
            "task_type": self.task_type,
            "status": self.status.value,
            "status_label_cn": self.status.label_cn,
            "dependencies": self.dependencies,
            "risk_level": self.risk_level.value,
            "risk_label_cn": self.risk_level.label_cn,
            "required_evidence": self.required_evidence,
            "source_refs": self.source_refs,
            "requires_human_confirmation": self.requires_human_confirmation,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AssignmentValidation:
    valid: bool
    message_cn: str
    details: list[str] = field(default_factory=list)
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "message_cn": self.message_cn,
            "details": self.details,
            "blocked": self.blocked,
        }


# ── Service ─────────────────────────────────────────────────────────────

class SubtaskAssignmentService:

    def __init__(self) -> None:
        self._assignments: dict[str, SubtaskAssignment] = {}

    # ── Create ──────────────────────────────────────────────────────

    def create_assignment(
        self,
        title_cn: str,
        description_cn: str,
        assigned_role: str,
        task_type: str,
        dependencies: list[str] | None = None,
        risk_level: str = "low",
        required_evidence: list[str] | None = None,
        source_refs: list[str] | None = None,
    ) -> AssignmentValidation | SubtaskAssignment:
        """Create a subtask with role compatibility and dependency checks."""

        # Validate role
        if assigned_role not in _ROLE_ACTIONS:
            return AssignmentValidation(
                valid=False,
                message_cn=f"无效角色：{assigned_role}。有效角色：{', '.join(_ROLE_ACTIONS.keys())}。",
                blocked=True,
            )

        # Validate task_type
        valid_types = {"plan", "research", "build", "review"}
        if task_type not in valid_types:
            return AssignmentValidation(
                valid=False,
                message_cn=f"无效任务类型：{task_type}。有效类型：{', '.join(sorted(valid_types))}。",
                blocked=True,
            )

        # Role compatibility
        role_actions = _ROLE_ACTIONS.get(assigned_role, {})
        if not role_actions.get(task_type, False):
            return AssignmentValidation(
                valid=False,
                message_cn=f"角色 {assigned_role} 不能执行 {task_type} 类型任务。",
                details=[f"{assigned_role} 只能执行：{', '.join(k for k, v in role_actions.items() if v)}。"],
                blocked=True,
            )

        # Researcher cannot write/execute
        if assigned_role == "researcher":
            if task_type in ("build", "plan"):
                return AssignmentValidation(
                    valid=False,
                    message_cn="研究员不能执行写操作任务。研究员只能进行只读调研。",
                    blocked=True,
                )

        # Reviewer cannot be assigned to Builder
        if assigned_role == "reviewer" and task_type == "build":
            return AssignmentValidation(
                valid=False,
                message_cn="审查者不能执行构建任务。审查者只负责独立审查。",
                blocked=True,
            )

        # Risk level
        try:
            risk = RiskLevel(risk_level)
        except ValueError:
            return AssignmentValidation(
                valid=False,
                message_cn=f"无效风险等级：{risk_level}。有效值：low/medium/high/critical。",
                blocked=True,
            )

        # Dependency check: only validate existence at creation time
        deps = dependencies or []
        for dep_id in deps:
            dep = self._assignments.get(dep_id)
            if dep is None:
                return AssignmentValidation(
                    valid=False,
                    message_cn=f"依赖任务不存在：{dep_id}。",
                    blocked=True,
                )

        now = datetime.now(timezone.utc).isoformat()
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        assignment = SubtaskAssignment(
            task_id=task_id,
            title_cn=title_cn,
            description_cn=description_cn,
            assigned_role=assigned_role,
            task_type=task_type,
            status=SubtaskStatus.PENDING,
            dependencies=deps,
            risk_level=risk,
            required_evidence=required_evidence or [],
            source_refs=source_refs or [],
            requires_human_confirmation=risk.requires_human,
            created_at=now,
            updated_at=now,
        )
        self._assignments[task_id] = assignment
        return assignment

    # ── Read ────────────────────────────────────────────────────────

    def list_assignments(self, role: str | None = None, status: str | None = None) -> list[SubtaskAssignment]:
        results = list(self._assignments.values())
        if role:
            results = [a for a in results if a.assigned_role == role]
        if status:
            results = [a for a in results if a.status.value == status]
        return results

    def get_assignment(self, task_id: str) -> Optional[SubtaskAssignment]:
        return self._assignments.get(task_id)

    def board_summary_cn(self) -> dict:
        """Chinese board summary with counts per status and role."""
        all_tasks = list(self._assignments.values())
        by_status: dict[str, int] = {}
        by_role: dict[str, int] = {}
        blocked_tasks: list[dict] = []

        for a in all_tasks:
            by_status[a.status.label_cn] = by_status.get(a.status.label_cn, 0) + 1
            by_role[a.assigned_role] = by_role.get(a.assigned_role, 0) + 1
            if a.status == SubtaskStatus.BLOCKED:
                blocked_tasks.append({
                    "task_id": a.task_id,
                    "title_cn": a.title_cn,
                    "assigned_role": a.assigned_role,
                    "risk_level": a.risk_level.value,
                })

        return {
            "total_tasks": len(all_tasks),
            "by_status": by_status,
            "by_role": by_role,
            "blocked_tasks": blocked_tasks,
            "note": "此面板为只读状态摘要，不提供执行、批准、删除功能。",
        }

    # ── Update ──────────────────────────────────────────────────────

    def update_status(
        self,
        task_id: str,
        new_status: str,
    ) -> AssignmentValidation:
        """Update a subtask's status with validation."""
        assignment = self._assignments.get(task_id)
        if assignment is None:
            return AssignmentValidation(
                valid=False, message_cn=f"未找到任务：{task_id}。", blocked=True,
            )

        try:
            status = SubtaskStatus(new_status)
        except ValueError:
            return AssignmentValidation(
                valid=False,
                message_cn=f"无效状态：{new_status}。有效值：{', '.join(s.value for s in SubtaskStatus)}。",
                blocked=True,
            )

        # Dependency check when moving to READY
        if status == SubtaskStatus.READY:
            for dep_id in assignment.dependencies:
                dep = self._assignments.get(dep_id)
                if dep is None or dep.status != SubtaskStatus.COMPLETED:
                    return AssignmentValidation(
                        valid=False,
                        message_cn=f"依赖任务 {dep_id} 未完成，不能进入就绪状态。",
                        blocked=True,
                    )

        assignment.status = status
        assignment.updated_at = datetime.now(timezone.utc).isoformat()
        return AssignmentValidation(
            valid=True,
            message_cn=f"任务 {assignment.title_cn} 状态更新为 {status.label_cn}。",
        )
