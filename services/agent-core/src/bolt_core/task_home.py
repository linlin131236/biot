"""Task Home Service (M91). Read-only aggregation of task home data from
existing services: goals, permissions, diagnostics, planner graphs.

Aggregates a single GET /task-home endpoint that the desktop home panel
consumes as its first-screen dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TaskHomeSummary:
    current_goal: Optional[dict] = None
    unfinished_goal_count: int = 0
    pending_permission_count: int = 0
    blocker_count: int = 0
    warning_count: int = 0
    active_task_count: int = 0
    recent_events: list[dict] = field(default_factory=list)
    next_suggestions: list[str] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "current_goal": self.current_goal,
            "unfinished_goal_count": self.unfinished_goal_count,
            "pending_permission_count": self.pending_permission_count,
            "blocker_count": self.blocker_count,
            "warning_count": self.warning_count,
            "active_task_count": self.active_task_count,
            "recent_events": self.recent_events,
            "next_suggestions": self.next_suggestions,
            "updated_at": self.updated_at,
        }


_STATUS_CN: dict[str, str] = {
    "pending": "待开始",
    "running": "运行中",
    "paused": "已暂停",
    "completed": "已完成",
    "failed": "已失败",
    "stopped": "已停止",
    "rejected": "已拒绝",
}


class TaskHomeService:
    """Read-only aggregation of task home data from existing services.

    Accepts references to harness, diagnostics, and planner — all read-only
    from this service's perspective. No write, approve, delete, or execute.
    """

    def __init__(self, harness, diagnostics_service, planner_service):
        self._harness = harness
        self._diagnostics = diagnostics_service
        self._planner = planner_service

    # ── Public API ──────────────────────────────────────────────────

    def get_summary(self) -> TaskHomeSummary:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        goals_data = self._collect_goals()
        perm_count = self._collect_permissions()
        blockers, warnings, diags = self._collect_diagnostics()
        task_count = self._collect_planner()
        recent = self._build_recent_events(diags)
        suggestions = self._generate_suggestions(
            goals_data, blockers, warnings, perm_count, task_count,
        )

        return TaskHomeSummary(
            current_goal=goals_data.get("current"),
            unfinished_goal_count=goals_data.get("count", 0),
            pending_permission_count=perm_count,
            blocker_count=blockers,
            warning_count=warnings,
            active_task_count=task_count,
            recent_events=recent,
            next_suggestions=suggestions,
            updated_at=now,
        )

    # ── Collectors ──────────────────────────────────────────────────

    def _collect_goals(self) -> dict:
        try:
            goals = self._harness.goals.unfinished_goals()
            goal_dicts = [g.to_dict() for g in goals]
            current = None
            for g in goal_dicts:
                if g.get("status") == "running":
                    current = g
                    break
            if current is None and goal_dicts:
                current = goal_dicts[0]
            return {"current": current, "count": len(goal_dicts), "all": goal_dicts}
        except Exception:
            return {"current": None, "count": 0, "all": []}

    def _collect_permissions(self) -> int:
        try:
            return len(self._harness.permissions.pending_permissions())
        except Exception:
            return 0

    def _collect_diagnostics(self) -> tuple[int, int, list[dict]]:
        try:
            diags = self._diagnostics.list_diagnostics()
            blockers = sum(1 for d in diags if d.get("severity") == "blocking")
            warnings = sum(1 for d in diags if d.get("severity") == "warning")
            return blockers, warnings, diags
        except Exception:
            return 0, 0, []

    def _collect_planner(self) -> int:
        try:
            return len(self._planner.list_graphs())
        except Exception:
            return 0

    def _build_recent_events(self, diags: list[dict]) -> list[dict]:
        events: list[dict] = []
        try:
            for d in diags[:5]:
                events.append({
                    "code": d.get("code", ""),
                    "severity": d.get("severity", ""),
                    "severity_label": d.get("severity_label", ""),
                    "summary": d.get("summary", ""),
                    "suggestion": d.get("suggestion", ""),
                })
        except Exception:
            pass
        return events

    # ── Suggestions ─────────────────────────────────────────────────

    def _generate_suggestions(
        self,
        goals_data: dict,
        blockers: int,
        warnings: int,
        perm_count: int,
        task_count: int,
    ) -> list[str]:
        suggestions: list[str] = []
        current = goals_data.get("current")
        goals = goals_data.get("all", [])

        # Priority: blockers first
        if blockers > 0:
            suggestions.append(
                f"当前有 {blockers} 个阻断项需要处理，请查看诊断中心了解详情。"
            )
        if warnings > 0:
            suggestions.append(
                f"当前有 {warnings} 个警告项，建议复查后再继续执行。"
            )
        if perm_count > 0:
            suggestions.append(
                f"有 {perm_count} 个权限请求等待批准，请前往权限中心处理。"
            )

        # Goal status
        if current is not None:
            obj = current.get("objective", "未命名目标")
            status = current.get("status", "")
            status_cn = _STATUS_CN.get(status, status)
            suggestions.append(f"当前目标「{obj}」状态：{status_cn}。")

            if status == "paused":
                suggestions.append("当前目标已暂停，可以在目标面板恢复执行。")
            elif status == "failed":
                suggestions.append(
                    "当前目标已失败，请查看失败解释面板了解原因和重试建议。"
                )
        elif len(goals) > 0:
            suggestions.append(f"有 {len(goals)} 个未完成目标等待执行。")
        else:
            suggestions.append("当前没有进行中的目标，可以创建一个新目标开始工作。")

        if task_count > 0:
            suggestions.append(f"有 {task_count} 个 Planner 任务图处于活跃状态。")

        return suggestions
