"""Task Home API router (M91). Read-only endpoint for the desktop home panel.

Single GET /task-home returns an aggregated summary of the current state:
goals, permissions, diagnostics, planner graphs, and Chinese suggestions.
"""
from fastapi import APIRouter

from bolt_core.task_home import TaskHomeService


def create_task_home_router(harness, diagnostics_service, planner_service) -> APIRouter:
    router = APIRouter(tags=["task-home"])
    service = TaskHomeService(harness, diagnostics_service, planner_service)

    @router.get("/task-home")
    def get_task_home() -> dict:
        """获取中文任务首页聚合摘要。只读。

        返回字段：
        - current_goal: 当前运行中或最近的目标摘要
        - unfinished_goal_count: 未完成目标数量
        - pending_permission_count: 等待批准的权限数量
        - blocker_count: 诊断阻断项数量
        - warning_count: 诊断警告项数量
        - active_task_count: 活跃 Planner 任务图数量
        - recent_events: 最近 5 条诊断事件
        - next_suggestions: 中文下一步建议列表
        - updated_at: 数据更新时间

        示例：GET /task-home
        """
        return service.get_summary().to_dict()

    return router
