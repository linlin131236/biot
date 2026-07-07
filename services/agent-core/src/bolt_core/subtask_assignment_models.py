"""Subtask Assignment data models: statuses, risk levels, role compatibility.

Extracted from subtask_assignment.py to respect the 300-line size gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SubtaskStatus(str, Enum):
    PENDING = "pending"; READY = "ready"; IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"; AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"; FAILED = "failed"

    @property
    def label_cn(self) -> str:
        return {"pending": "待办", "ready": "就绪", "in_progress": "进行中",
                "blocked": "阻塞", "awaiting_review": "待审查",
                "completed": "已完成", "failed": "已失败"}.get(self.value, self.value)


class RiskLevel(str, Enum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

    @property
    def label_cn(self) -> str:
        return {"low": "低", "medium": "中", "high": "高", "critical": "严重"}.get(self.value, self.value)

    @property
    def requires_human(self) -> bool:
        return self in (RiskLevel.HIGH, RiskLevel.CRITICAL)


_ROLE_ACTIONS: dict[str, dict[str, bool]] = {
    "planner": {"plan": True, "research": False, "build": False, "review": False},
    "researcher": {"plan": False, "research": True, "build": False, "review": False},
    "builder": {"plan": False, "research": False, "build": True, "review": False},
    "reviewer": {"plan": False, "research": False, "build": False, "review": True},
    "skill_learner": {"plan": False, "research": False, "build": False, "review": False},
}


@dataclass
class SubtaskAssignment:
    task_id: str; title_cn: str; description_cn: str; assigned_role: str
    task_type: str; status: SubtaskStatus; dependencies: list[str]
    risk_level: RiskLevel; required_evidence: list[str]; source_refs: list[str]
    requires_human_confirmation: bool; created_at: str; updated_at: str

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "title_cn": self.title_cn,
            "description_cn": self.description_cn, "assigned_role": self.assigned_role,
            "task_type": self.task_type, "status": self.status.value,
            "status_label_cn": self.status.label_cn, "dependencies": self.dependencies,
            "risk_level": self.risk_level.value, "risk_label_cn": self.risk_level.label_cn,
            "required_evidence": self.required_evidence, "source_refs": self.source_refs,
            "requires_human_confirmation": self.requires_human_confirmation,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


@dataclass
class AssignmentValidation:
    valid: bool; message_cn: str
    details: list[str] = field(default_factory=list)
    blocked: bool = False

    def to_dict(self) -> dict:
        return {"valid": self.valid, "message_cn": self.message_cn,
                "details": self.details, "blocked": self.blocked}
