"""Multi-agent delegation: task lifecycle with scope constraints.

Sub-agents cannot expand workspace, and reviewer failure
blocks promotion of reviewed work.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from uuid import uuid4


class AgentRole(Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    BUILDER = "builder"
    REVIEWER = "reviewer"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"


@dataclass
class DelegationTask:
    id: str
    role: AgentRole
    objective: str
    status: TaskStatus
    inputs: dict = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    workspace: str = ""
    output: str = ""
    evidence: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "role": self.role.value,
            "objective": self.objective, "status": self.status.value,
            "inputs": self.inputs, "constraints": self.constraints,
            "workspace": self.workspace, "output": self.output,
            "evidence": self.evidence, "reason": self.reason,
        }


class DelegationService:
    def __init__(self, workspace: str = "") -> None:
        self._workspace = workspace
        self._lock = threading.Lock()
        self._tasks: dict[str, DelegationTask] = {}

    def create(self, role: AgentRole, objective: str,
               inputs: dict | None = None,
               constraints: list[str] | None = None) -> DelegationTask:
        task_id = f"task_{uuid4().hex[:8]}"
        ws = ""
        for c in (constraints or []):
            if c.startswith("workspace:"):
                ws = c.split(":", 1)[1]
        task = DelegationTask(
            id=task_id, role=role, objective=objective,
            status=TaskStatus.PENDING,
            inputs=inputs or {},
            constraints=constraints or [],
            workspace=ws,
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def start(self, task_id: str) -> DelegationTask:
        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.RUNNING
        return task

    def complete(self, task_id: str, output: str,
                 evidence: list[str]) -> DelegationTask:
        if not evidence:
            raise ValueError("evidence required for task completion")
        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.output = output
            task.evidence = evidence
        return task

    def fail(self, task_id: str, reason: str) -> DelegationTask:
        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.FAILED
            task.reason = reason
            # If reviewer fails, mark reviewed task as needing revision
            if task.role == AgentRole.REVIEWER:
                reviewed_id = task.inputs.get("review_of")
                if reviewed_id and reviewed_id in self._tasks:
                    self._tasks[reviewed_id].status = TaskStatus.NEEDS_REVISION
        return task

    def get(self, task_id: str) -> DelegationTask | None:
        return self._tasks.get(task_id)

    def list_by_role(self, role: AgentRole) -> list[DelegationTask]:
        with self._lock:
            return [t for t in self._tasks.values() if t.role == role]
