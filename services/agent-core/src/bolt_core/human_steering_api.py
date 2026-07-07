"""Human Steering API router. Safe steering endpoint, never auto-executes."""
from fastapi import APIRouter, HTTPException

from bolt_core.human_steering import HumanSteeringService
from bolt_core.pause_resume import PauseResumeService


def create_human_steering_router() -> APIRouter:
    """Create router for human steering operations.

    The steering endpoint classifies user intent and returns a safe action plan.
    It NEVER executes dangerous actions, approves permissions, or writes files.
    """
    router = APIRouter(tags=["human-steering"])
    pause_service = PauseResumeService()
    service = HumanSteeringService(pause_service=pause_service)

    @router.post("/runs/{run_id}/steering")
    def steer_run(run_id: str, payload: dict) -> dict:
        """Process a human steering input for a running task.

        Classifies intent (continue/pause/change_goal/request_review/abort/unknown),
        returns a Chinese explanation, and indicates whether human confirmation is needed.

        Safety: NEVER approves permissions, executes shell, or writes files.
        Side-effect intents (change_goal, abort) go to pending state only.
        Pause delegates to M66 PauseResumeService.
        """
        content = str(payload.get("content", ""))
        if not content.strip():
            raise HTTPException(status_code=400, detail="steering content 不能为空。")

        # Optional M66 integration: node_id and current_status for pause
        node_id = payload.get("node_id")
        current_status = payload.get("current_status")

        result = service.process(
            run_id=run_id,
            content=content,
            current_node_id=str(node_id) if node_id else None,
            current_status=str(current_status) if current_status else None,
        )
        return result.to_dict()

    return router
