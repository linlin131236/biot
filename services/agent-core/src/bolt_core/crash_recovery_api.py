"""M121 crash recovery readiness API. Read-only."""
from fastapi import APIRouter

from bolt_core.crash_recovery import CrashRecoveryService


def create_crash_recovery_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["reliability"])

    @router.get("/reliability/crash-recovery")
    def crash_recovery_review() -> dict:
        result = CrashRecoveryService(project_dir).review()
        return {
            "review": result.to_dict(),
            "disclaimer": "只读恢复准备度检查，不会执行恢复、发布或权限批准。",
        }

    return router
