"""Pause/resume API. Manages pause lifecycle, never auto-executes."""
from fastapi import APIRouter, HTTPException

from bolt_core.pause_resume import PauseResumeService


def create_pause_resume_router() -> APIRouter:
    router = APIRouter(tags=["pause-resume"])
    service = PauseResumeService()

    @router.post("/pause-resume/pause")
    def pause_node(payload: dict) -> dict:
        """Pause a task node. Captures a state snapshot."""
        node_id = str(payload.get("node_id", ""))
        if not node_id.strip():
            raise HTTPException(status_code=400, detail="node_id is required")
        current_status = str(payload.get("current_status", ""))
        if not current_status:
            raise HTTPException(status_code=400, detail="current_status is required")
        reason = str(payload.get("reason", ""))
        evidence_refs = payload.get("evidence_refs")
        try:
            return service.pause(node_id, current_status, reason, evidence_refs)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/pause-resume/resume")
    def resume_node(payload: dict) -> dict:
        """Resume a paused node. Re-verifies safety, returns action plan."""
        node_id = str(payload.get("node_id", ""))
        if not node_id.strip():
            raise HTTPException(status_code=400, detail="node_id is required")
        recheck = bool(payload.get("recheck_permissions", True))
        try:
            return service.resume(node_id, recheck)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/pause-resume/cancel")
    def cancel_pause(payload: dict) -> dict:
        """Cancel a pause, marking the node as failed."""
        node_id = str(payload.get("node_id", ""))
        if not node_id.strip():
            raise HTTPException(status_code=400, detail="node_id is required")
        try:
            return service.cancel_pause(node_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/pause-resume/status/{node_id}")
    def pause_status(node_id: str) -> dict:
        """Check if a node is paused and get its snapshot."""
        return {
            "node_id": node_id,
            "is_paused": service.is_paused(node_id),
            "snapshot": service.get_snapshot(node_id),
        }

    @router.get("/pause-resume/paused")
    def list_paused() -> dict:
        """List all paused node IDs."""
        return {"paused_nodes": service.get_paused_nodes()}

    return router
