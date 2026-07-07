"""Subtask Assignment API router."""
from fastapi import APIRouter, HTTPException, Query

from bolt_core.subtask_assignment import SubtaskAssignmentService


def create_subtask_assignment_router() -> APIRouter:
    router = APIRouter(tags=["subtask-assignment"])
    service = SubtaskAssignmentService()

    @router.post("/subtasks")
    def create_assignment(payload: dict) -> dict:
        """创建子任务。Planner 拆解任务用。

        required: title_cn, description_cn, assigned_role, task_type
        optional: dependencies, risk_level, required_evidence, source_refs
        """
        result = service.create_assignment(
            title_cn=payload.get("title_cn", ""),
            description_cn=payload.get("description_cn", ""),
            assigned_role=payload.get("assigned_role", ""),
            task_type=payload.get("task_type", ""),
            dependencies=payload.get("dependencies"),
            risk_level=payload.get("risk_level", "low"),
            required_evidence=payload.get("required_evidence"),
            source_refs=payload.get("source_refs"),
        )
        if hasattr(result, 'blocked') and result.blocked:
            raise HTTPException(status_code=400, detail=result.message_cn)
        if not hasattr(result, 'valid'):
            return result.to_dict()
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.get("/subtasks")
    def list_assignments(
        role: str | None = Query(default=None),
        status: str | None = Query(default=None),
    ) -> list[dict]:
        """列出子任务，可按角色/状态筛选。只读。"""
        return [a.to_dict() for a in service.list_assignments(role, status)]

    @router.get("/subtasks/{task_id}")
    def get_assignment(task_id: str) -> dict:
        """获取子任务详情。只读。"""
        a = service.get_assignment(task_id)
        if a is None:
            raise HTTPException(status_code=404, detail=f"未找到任务：{task_id}。")
        return a.to_dict()

    @router.get("/subtasks/board/summary")
    def board_summary() -> dict:
        """获取子任务看板中文摘要（按状态/角色统计）。只读。"""
        return service.board_summary_cn()

    @router.post("/subtasks/{task_id}/status")
    def update_status(task_id: str, payload: dict) -> dict:
        """更新子任务状态。

        payload: { new_status: str }
        检查依赖完成情况后才允许就绪。
        """
        result = service.update_status(task_id, payload.get("new_status", ""))
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    return router
