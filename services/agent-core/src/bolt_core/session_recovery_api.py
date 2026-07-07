"""Session Recovery API (M98). Self-contained, creates its own services."""
from fastapi import APIRouter

from bolt_core.recovery_policy import RecoveryPolicyService
from bolt_core.pause_resume import PauseResumeService


def create_session_recovery_router() -> APIRouter:
    router = APIRouter(tags=["session-recovery"])
    recovery = RecoveryPolicyService()
    pause_resume = PauseResumeService()

    @router.get("/session-recovery")
    def get_session_recovery() -> dict:
        policy: dict = {}
        try:
            policy = recovery.get_policy()
        except Exception:
            pass

        paused: list[dict] = []
        try:
            paused = pause_resume.list_paused()
        except Exception:
            pass

        return {"paused_tasks": paused, "total_paused": len(paused), "recovery_policy": policy}

    return router
