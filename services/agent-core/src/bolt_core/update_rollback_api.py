"""M123 update and rollback readiness API. Read-only."""
from fastapi import APIRouter

from bolt_core.update_rollback import UpdateRollbackReadinessService


def create_update_rollback_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["reliability"])

    @router.get("/reliability/update-rollback")
    def update_rollback_review() -> dict:
        result = UpdateRollbackReadinessService(project_dir).review()
        return {
            "review": result.to_dict(),
            "disclaimer": "只读升级回滚准备度检查，不会发布、回滚、打 tag 或删除文件。",
        }

    return router
