"""Execution audit timeline API. Read-only audit summaries only."""
from fastapi import APIRouter, HTTPException

from bolt_core.execution_audit_timeline import ExecutionAuditTimelineService
from bolt_core.task_closure_service import TaskClosureService


def create_execution_audit_timeline_router(
    timeline_service: ExecutionAuditTimelineService,
    task_closure_service: TaskClosureService,
) -> APIRouter:
    router = APIRouter(tags=["execution-audit"])

    @router.get("/task-closures/{closure_id}/execution-audit-timeline")
    def execution_audit_timeline(closure_id: str) -> list[dict]:
        if task_closure_service.load(closure_id) is None:
            raise HTTPException(status_code=404, detail="任务闭环不存在")
        return timeline_service.for_closure(closure_id)

    return router
