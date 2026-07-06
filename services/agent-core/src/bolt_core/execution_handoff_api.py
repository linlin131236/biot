"""Execution handoff API. Creates safe handoff records only; no execution."""
from fastapi import APIRouter, HTTPException, Query

from bolt_core.execution_handoff import ExecutionHandoffInvalidTransition, ExecutionHandoffNotFound, ExecutionHandoffService
from bolt_core.execution_permission_bridge import ExecutionPermissionBridgeInvalidRequest, ExecutionPermissionBridgeService
from bolt_core.execution_queue import ExecutionQueueItemNotFound, ExecutionQueueService


def create_execution_handoff_router(
    handoff_service: ExecutionHandoffService,
    queue_service: ExecutionQueueService,
    permission_bridge: ExecutionPermissionBridgeService | None = None,
    permission_run_id: str = "execution_bridge",
) -> APIRouter:
    router = APIRouter(tags=["execution-handoff"])

    @router.get("/execution-handoffs")
    def list_execution_handoffs(closure_id: str | None = Query(default=None)) -> list[dict]:
        return [record.to_dict() for record in handoff_service.list_records(closure_id)]

    @router.post("/execution-queue/{item_id}/handoff")
    def create_execution_handoff(item_id: str) -> dict:
        try:
            item = queue_service.get_item(item_id)
        except ExecutionQueueItemNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        if item.status != "approved":
            raise HTTPException(status_code=409, detail="队列项必须先批准")
        return handoff_service.create_from_queue_item(item).to_dict()

    @router.post("/execution-handoffs/{handoff_id}/complete")
    def complete_execution_handoff(handoff_id: str, payload: dict) -> dict:
        return _handoff_response(lambda: handoff_service.complete(handoff_id, str(payload.get("result", ""))))

    @router.post("/execution-handoffs/{handoff_id}/fail")
    def fail_execution_handoff(handoff_id: str, payload: dict) -> dict:
        return _handoff_response(lambda: handoff_service.fail(handoff_id, str(payload.get("result", ""))))

    @router.post("/execution-handoffs/{handoff_id}/request-permission")
    def request_execution_handoff_permission(handoff_id: str) -> dict:
        if permission_bridge is None:
            raise HTTPException(status_code=409, detail="执行权限桥接未启用")
        return _handoff_response(lambda: permission_bridge.request_permission(handoff_id, permission_run_id))

    return router


def _handoff_response(action) -> dict:
    try:
        return action().to_dict()
    except ExecutionHandoffNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ExecutionHandoffInvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ExecutionPermissionBridgeInvalidRequest as exc:
        raise HTTPException(status_code=409, detail=str(exc))
