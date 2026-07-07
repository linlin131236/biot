"""Multi-Task Queue API (M96). Aggregates closures, goals, and planner graphs."""
from fastapi import APIRouter


def create_multi_task_queue_router(harness, closure_service, planner_service) -> APIRouter:
    router = APIRouter(tags=["multi-task-queue"])

    @router.get("/multi-task-queue")
    def get_multi_task_queue(status: str | None = None) -> dict:
        """获取多任务队列视图。只读。

        聚合任务闭环、目标和计划任务图。
        示例：GET /multi-task-queue?status=running
        """
        closures: list[dict] = []
        goals: list[dict] = []
        graphs: list[dict] = []

        try:
            closures = closure_service.list_closures()
            if status and status != "all":
                closures = [c for c in closures if c.get("status") == status]
        except Exception:
            pass
        try:
            goals = [g.to_dict() for g in harness.goal_service.unfinished_goals()]
        except Exception:
            pass
        try:
            graphs = planner_service.list_graphs()
        except Exception:
            pass

        tasks: list[dict] = []
        for c in closures:
            tasks.append({
                "type": "closure", "id": c.get("id", ""), "title": c.get("objective", ""),
                "status": c.get("status", ""), "risk": "medium",
            })
        for g in goals:
            tasks.append({
                "type": "goal", "id": g.get("id", ""), "title": g.get("objective", ""),
                "status": g.get("status", ""), "risk": "low",
            })
        for gr in graphs:
            tasks.append({
                "type": "graph", "id": gr.get("id", ""), "title": gr.get("title", ""),
                "status": "active", "risk": "low",
            })

        return {
            "tasks": tasks,
            "total": len(tasks),
            "closures_count": len(closures),
            "goals_count": len(goals),
            "graphs_count": len(graphs),
        }

    return router
