import re
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class GoalStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"
    REJECTED = "rejected"


_VAGUE_PATTERNS = [
    re.compile(r"^\s*(do\s+stuff|fix\s+things|make\s+it\s+work|help\s+me|something)\s*$", re.IGNORECASE),
]


@dataclass(frozen=True)
class Goal:
    id: str = field(default_factory=lambda: f"goal_{uuid4().hex[:8]}")
    objective: str = ""
    criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    workspace: str = ""
    max_steps: int = 100
    max_cost: float = 5.0
    max_wall_time: int = 3600
    step_count: int = 0
    rejection_reason: str = ""
    file_snapshot: dict[str, str] = field(default_factory=dict)

    def with_status(self, status: GoalStatus) -> "Goal":
        if self.status == GoalStatus.COMPLETED:
            return self
        if self.status == GoalStatus.REJECTED:
            return self
        if self.status == GoalStatus.STOPPED and status != GoalStatus.PENDING:
            return self
        return Goal(
            id=self.id, objective=self.objective, criteria=self.criteria,
            constraints=self.constraints, status=status, workspace=self.workspace,
            max_steps=self.max_steps, max_cost=self.max_cost,
            max_wall_time=self.max_wall_time, step_count=self.step_count,
            rejection_reason=self.rejection_reason,
            file_snapshot=self.file_snapshot,
        )

    def with_snapshot(self, snapshot: dict[str, str]) -> "Goal":
        return Goal(
            id=self.id, objective=self.objective, criteria=self.criteria,
            constraints=self.constraints, status=self.status,
            workspace=self.workspace, max_steps=self.max_steps,
            max_cost=self.max_cost, max_wall_time=self.max_wall_time,
            step_count=self.step_count, rejection_reason=self.rejection_reason,
            file_snapshot=snapshot,
        )

    def with_step(self, step_count: int) -> "Goal":
        return Goal(
            id=self.id, objective=self.objective, criteria=self.criteria,
            constraints=self.constraints, status=self.status,
            workspace=self.workspace, max_steps=self.max_steps,
            max_cost=self.max_cost, max_wall_time=self.max_wall_time,
            step_count=step_count, rejection_reason=self.rejection_reason,
            file_snapshot=self.file_snapshot,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "objective": self.objective,
            "criteria": self.criteria, "constraints": self.constraints,
            "status": self.status.value, "workspace": self.workspace,
            "max_steps": self.max_steps, "max_cost": self.max_cost,
            "max_wall_time": self.max_wall_time, "step_count": self.step_count,
            "rejection_reason": self.rejection_reason,
            "file_snapshot": self.file_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Goal":
        data = dict(data)
        data["status"] = GoalStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class GoalBuilder:
    def build(self, objective: str, criteria: list[str] | None = None,
              constraints: list[str] | None = None, workspace: str = "",
              max_steps: int = 100, max_cost: float = 5.0,
              max_wall_time: int = 3600) -> Goal:
        if self._is_too_vague(objective):
            return Goal(
                objective=objective, criteria=criteria or [],
                constraints=constraints or [], status=GoalStatus.REJECTED,
                workspace=workspace, max_steps=max_steps, max_cost=max_cost,
                max_wall_time=max_wall_time,
                rejection_reason="Goal is too vague to audit. Provide specific completion criteria.",
            )
        inferred = criteria or self._infer_criteria(objective)
        return Goal(
            objective=objective, criteria=inferred,
            constraints=constraints or [], status=GoalStatus.PENDING,
            workspace=workspace, max_steps=max_steps, max_cost=max_cost,
            max_wall_time=max_wall_time,
        )

    def _is_too_vague(self, objective: str) -> bool:
        for pattern in _VAGUE_PATTERNS:
            if pattern.match(objective):
                return True
        return False

    def _infer_criteria(self, objective: str) -> list[str]:
        return [f"Objective met: {objective}"]
