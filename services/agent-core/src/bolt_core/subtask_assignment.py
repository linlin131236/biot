"""Subtask Assignment Service. Planner creates structured tasks with role
compatibility, dependency, and risk checks. Never auto-executes.

Data models in subtask_assignment_models.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

from bolt_core.subtask_assignment_models import (
    SubtaskStatus, RiskLevel, SubtaskAssignment, AssignmentValidation,
    _ROLE_ACTIONS,
)


class SubtaskAssignmentService:

    def __init__(self) -> None:
        self._assignments: dict[str, SubtaskAssignment] = {}

    def create_assignment(self, title_cn: str, description_cn: str,
                          assigned_role: str, task_type: str,
                          dependencies: list[str] | None = None,
                          risk_level: str = "low",
                          required_evidence: list[str] | None = None,
                          source_refs: list[str] | None = None,
                          ) -> AssignmentValidation | SubtaskAssignment:
        if assigned_role not in _ROLE_ACTIONS:
            return AssignmentValidation(False, f"无效角色：{assigned_role}。", blocked=True)
        if task_type not in ("plan", "research", "build", "review"):
            return AssignmentValidation(False, f"无效任务类型：{task_type}。", blocked=True)
        role_actions = _ROLE_ACTIONS.get(assigned_role, {})
        if not role_actions.get(task_type, False):
            allowed = ', '.join(k for k, v in role_actions.items() if v)
            return AssignmentValidation(False, f"角色 {assigned_role} 不能执行 {task_type}。允许：{allowed}。", blocked=True)
        if assigned_role == "researcher" and task_type in ("build", "plan"):
            return AssignmentValidation(False, "研究员不能执行写操作任务。", blocked=True)
        if assigned_role == "reviewer" and task_type == "build":
            return AssignmentValidation(False, "审查者不能执行构建任务。", blocked=True)
        try:
            risk = RiskLevel(risk_level)
        except ValueError:
            return AssignmentValidation(False, f"无效风险等级：{risk_level}。", blocked=True)
        deps = dependencies or []
        for dep_id in deps:
            if dep_id not in self._assignments:
                return AssignmentValidation(False, f"依赖任务不存在：{dep_id}。", blocked=True)
        now = datetime.now(timezone.utc).isoformat()
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        a = SubtaskAssignment(task_id=task_id, title_cn=title_cn, description_cn=description_cn,
                              assigned_role=assigned_role, task_type=task_type,
                              status=SubtaskStatus.PENDING, dependencies=deps, risk_level=risk,
                              required_evidence=required_evidence or [], source_refs=source_refs or [],
                              requires_human_confirmation=risk.requires_human,
                              created_at=now, updated_at=now)
        self._assignments[task_id] = a
        return a

    def list_assignments(self, role: str | None = None, status: str | None = None) -> list[SubtaskAssignment]:
        results = list(self._assignments.values())
        if role: results = [a for a in results if a.assigned_role == role]
        if status: results = [a for a in results if a.status.value == status]
        return results

    def get_assignment(self, task_id: str) -> Optional[SubtaskAssignment]:
        return self._assignments.get(task_id)

    def board_summary_cn(self) -> dict:
        all_tasks = list(self._assignments.values())
        by_status: dict[str, int] = {}; by_role: dict[str, int] = {}; blocked: list[dict] = []
        for a in all_tasks:
            by_status[a.status.label_cn] = by_status.get(a.status.label_cn, 0) + 1
            by_role[a.assigned_role] = by_role.get(a.assigned_role, 0) + 1
            if a.status == SubtaskStatus.BLOCKED:
                blocked.append({"task_id": a.task_id, "title_cn": a.title_cn,
                                "assigned_role": a.assigned_role, "risk_level": a.risk_level.value})
        return {"total_tasks": len(all_tasks), "by_status": by_status,
                "by_role": by_role, "blocked_tasks": blocked,
                "note": "此面板为只读状态摘要，不提供执行、批准、删除功能。"}

    def update_status(self, task_id: str, new_status: str) -> AssignmentValidation:
        a = self._assignments.get(task_id)
        if a is None:
            return AssignmentValidation(False, f"未找到任务：{task_id}。", blocked=True)
        try:
            status = SubtaskStatus(new_status)
        except ValueError:
            return AssignmentValidation(False, f"无效状态：{new_status}。", blocked=True)
        if status == SubtaskStatus.READY:
            for dep_id in a.dependencies:
                dep = self._assignments.get(dep_id)
                if dep is None or dep.status != SubtaskStatus.COMPLETED:
                    return AssignmentValidation(False, f"依赖任务 {dep_id} 未完成。", blocked=True)
        a.status = status
        a.updated_at = datetime.now(timezone.utc).isoformat()
        return AssignmentValidation(True, f"任务 {a.title_cn} 状态更新为 {status.label_cn}。")
