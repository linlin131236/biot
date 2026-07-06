"""Execution queue API. Human approval records only; no execution."""
from fastapi import APIRouter, HTTPException, Query

from bolt_core.execution_queue import ExecutionQueueInvalidTransition, ExecutionQueueItemNotFound, ExecutionQueueService
from bolt_core.task_closure_service import TaskClosureService


def create_execution_queue_router(
    queue_service: ExecutionQueueService,
    task_closure_service: TaskClosureService,
) -> APIRouter:
    router = APIRouter(tags=["execution-queue"])

    @router.get("/execution-queue")
    def list_execution_queue(closure_id: str | None = Query(default=None)) -> list[dict]:
        return [item.to_dict() for item in queue_service.list_items(closure_id)]

    @router.post("/task-closures/{closure_id}/execution-queue/propose")
    def propose_execution_queue(closure_id: str) -> list[dict]:
        _require_closure(task_closure_service, closure_id)
        return task_closure_service.propose_execution_items(closure_id, queue_service)

    @router.post("/execution-queue/{item_id}/approve")
    def approve_queue_item(item_id: str) -> dict:
        return _item_response(lambda: queue_service.approve(item_id))

    @router.post("/execution-queue/{item_id}/reject")
    def reject_queue_item(item_id: str, payload: dict) -> dict:
        return _item_response(lambda: queue_service.reject(item_id, str(payload.get("reason", ""))))

    @router.post("/execution-queue/{item_id}/complete")
    def complete_queue_item(item_id: str, payload: dict) -> dict:
        return _item_response(lambda: queue_service.mark_completed(item_id, str(payload.get("result", ""))))

    @router.post("/execution-queue/{item_id}/fail")
    def fail_queue_item(item_id: str, payload: dict) -> dict:
        return _item_response(lambda: queue_service.mark_failed(item_id, str(payload.get("result", ""))))

    return router


def _require_closure(service: TaskClosureService, closure_id: str) -> None:
    if service.load(closure_id) is None:
        raise HTTPException(status_code=404, detail="任务闭环不存在")


def _item_response(action) -> dict:
    try:
        return action().to_dict()
    except ExecutionQueueItemNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ExecutionQueueInvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
